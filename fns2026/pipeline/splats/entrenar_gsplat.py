"""
Entrena un Gaussian splat con gsplat (Apache-2.0, CUDA) a partir de lo que deja vistas_blender.py:
transforms.json (cámaras OpenGL de Blender), imágenes RGBA y puntos_iniciales.ply.

Es la alternativa a Brush para máquinas con NVIDIA sin Vulkan (Kaggle, Colab, servidores): mismas
entradas, misma salida (un .ply de 3DGS en el mundo de Blender, z arriba), así que podar_splat.py,
Unity y la web lo toman igual.

    python entrenar_gsplat.py CARPETA_VISTAS SALIDA.ply [--pasos 30000] [--sh 3]

Sigue el entrenador de referencia de gsplat (examples/simple_trainer.py v1.5.3): mismos learning
rates, estrategia de densificación por defecto y pérdida L1 + D-SSIM; suma una pérdida de alfa para
que el cielo y lo lejano (transparentes en las vistas) queden vacíos.
"""
import argparse
import json
import math
import os
import time

import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image


def argumentos():
    ap = argparse.ArgumentParser()
    ap.add_argument("carpeta")
    ap.add_argument("salida")
    ap.add_argument("--pasos", type=int, default=30000)
    ap.add_argument("--sh", type=int, default=3)
    ap.add_argument("--peso_ssim", type=float, default=0.2)
    ap.add_argument("--peso_alfa", type=float, default=0.1)
    ap.add_argument("--max_lado", type=int, default=1600, help="achica las vistas más grandes que esto")
    return ap.parse_args()


# ---------------------------------------------------------------------------------------------
# datos
# ---------------------------------------------------------------------------------------------

def leer_vistas(carpeta, archivo, max_lado, dispositivo):
    t = json.load(open(os.path.join(carpeta, archivo)))
    vistas = []
    for f in t["frames"]:
        img = Image.open(os.path.join(carpeta, f["file_path"])).convert("RGBA")
        w0, h0 = img.size
        k = min(1.0, max_lado / max(w0, h0))
        if k < 1:
            img = img.resize((round(w0 * k), round(h0 * k)), Image.LANCZOS)
        w, h = img.size
        pix = torch.from_numpy(np.asarray(img, np.float32) / 255.0)
        # Blender/NeRF: cámara OpenGL (mira a -Z, arriba +Y). gsplat usa OpenCV (mira a +Z, abajo +Y):
        # se dan vuelta las columnas Y y Z de la matriz cámara→mundo
        c2w = torch.tensor(f["transform_matrix"], dtype=torch.float32) @ torch.diag(torch.tensor([1.0, -1.0, -1.0, 1.0]))
        fx = t.get("fl_x", 0.5 * t["w"] / math.tan(t["camera_angle_x"] / 2)) * (w / t["w"])
        fy = t.get("fl_y", fx * t["w"] / w) * (h / t["h"])
        cx, cy = t.get("cx", t["w"] / 2) * (w / t["w"]), t.get("cy", t["h"] / 2) * (h / t["h"])
        K = torch.tensor([[fx, 0, cx], [0, fy, cy], [0, 0, 1]], dtype=torch.float32)
        vistas.append({"img": pix.to(dispositivo), "viewmat": torch.linalg.inv(c2w).to(dispositivo), "K": K.to(dispositivo), "w": w, "h": h})
    return vistas, t.get("ply_file_path")


def leer_puntos(ruta):
    with open(ruta, "rb") as f:
        props, n = [], 0
        while True:
            linea = f.readline().decode("ascii").strip()
            p = linea.split()
            if p[:2] == ["element", "vertex"]:
                n = int(p[2])
            elif p and p[0] == "property":
                props.append((p[2], {"float": "<f4", "uchar": "u1", "double": "<f8"}[p[1]]))
            elif linea == "end_header":
                break
        d = np.frombuffer(f.read(), dtype=np.dtype(props), count=n)
    pts = np.stack([d["x"], d["y"], d["z"]], 1).astype(np.float32)
    col = np.stack([d["red"], d["green"], d["blue"]], 1).astype(np.float32) / 255.0 if "red" in d.dtype.names else np.full_like(pts, 0.5)
    return torch.from_numpy(pts), torch.from_numpy(col)


# ---------------------------------------------------------------------------------------------
# splats
# ---------------------------------------------------------------------------------------------

SH_C0 = 0.28209479177387814


def iniciar(puntos, colores, sh, escena, dispositivo):
    n = len(puntos)
    # escala inicial: la distancia media a los 3 vecinos más cercanos (como simple_trainer)
    dist = torch.empty(n)
    for i in range(0, n, 4096):
        d = torch.cdist(puntos[i:i + 4096], puntos)
        dist[i:i + 4096] = d.topk(4, largest=False).values[:, 1:].mean(1)
    escalas = torch.log(dist.clamp_min(1e-4)).unsqueeze(1).repeat(1, 3)
    quats = torch.rand(n, 4)
    opac = torch.logit(torch.full((n,), 0.1))
    coef = torch.zeros(n, (sh + 1) ** 2, 3)
    coef[:, 0, :] = (colores - 0.5) / SH_C0
    lr = {"means": 1.6e-4 * escena, "scales": 5e-3, "quats": 1e-3, "opacities": 5e-2, "sh0": 2.5e-3, "shN": 2.5e-3 / 20}
    params = torch.nn.ParameterDict({
        "means": torch.nn.Parameter(puntos), "scales": torch.nn.Parameter(escalas), "quats": torch.nn.Parameter(quats),
        "opacities": torch.nn.Parameter(opac), "sh0": torch.nn.Parameter(coef[:, :1]), "shN": torch.nn.Parameter(coef[:, 1:]),
    }).to(dispositivo)
    opt = {k: torch.optim.Adam([{"params": params[k], "lr": lr[k], "name": k}], eps=1e-15) for k in params}
    return params, opt


def ssim(a, b, ventana=11):
    """SSIM con ventana gaussiana (a, b: [1, 3, H, W])."""
    g = torch.exp(-((torch.arange(ventana, device=a.device) - ventana // 2) ** 2) / (2 * 1.5 ** 2))
    g = (g / g.sum())
    k = (g[:, None] @ g[None, :]).expand(3, 1, ventana, ventana)
    mu_a, mu_b = F.conv2d(a, k, groups=3, padding=ventana // 2), F.conv2d(b, k, groups=3, padding=ventana // 2)
    s_a = F.conv2d(a * a, k, groups=3, padding=ventana // 2) - mu_a ** 2
    s_b = F.conv2d(b * b, k, groups=3, padding=ventana // 2) - mu_b ** 2
    s_ab = F.conv2d(a * b, k, groups=3, padding=ventana // 2) - mu_a * mu_b
    c1, c2 = 0.01 ** 2, 0.03 ** 2
    return (((2 * mu_a * mu_b + c1) * (2 * s_ab + c2)) / ((mu_a ** 2 + mu_b ** 2 + c1) * (s_a + s_b + c2))).mean()


def exportar(params, ruta):
    """El .ply de 3DGS de siempre (orden estándar de propiedades)."""
    m = params["means"].detach().cpu().numpy()
    sh0 = params["sh0"].detach().cpu().numpy().reshape(len(m), 3)
    shN = params["shN"].detach().cpu().transpose(1, 2).reshape(len(m), -1).numpy()   # por canal, como 3DGS
    cols = {"x": m[:, 0], "y": m[:, 1], "z": m[:, 2], "nx": 0 * m[:, 0], "ny": 0 * m[:, 0], "nz": 0 * m[:, 0]}
    cols.update({f"f_dc_{i}": sh0[:, i] for i in range(3)})
    cols.update({f"f_rest_{i}": shN[:, i] for i in range(shN.shape[1])})
    cols["opacity"] = params["opacities"].detach().cpu().numpy()
    s = params["scales"].detach().cpu().numpy()
    cols.update({f"scale_{i}": s[:, i] for i in range(3)})
    q = F.normalize(params["quats"].detach(), dim=-1).cpu().numpy()         # w, x, y, z
    cols.update({f"rot_{i}": q[:, i] for i in range(4)})
    datos = np.zeros(len(m), dtype=[(k, "<f4") for k in cols])
    for k, v in cols.items():
        datos[k] = v
    cab = ["ply", "format binary_little_endian 1.0", "comment FNS 2026: gsplat, mundo de Blender (z arriba)",
           f"element vertex {len(m)}"] + [f"property float {k}" for k in cols] + ["end_header"]
    with open(ruta, "wb") as f:
        f.write(("\n".join(cab) + "\n").encode("ascii"))
        f.write(datos.tobytes())


def main():
    a = argumentos()
    from gsplat import rasterization
    from gsplat.strategy import DefaultStrategy

    dev = "cuda"
    vistas, ply = leer_vistas(a.carpeta, "transforms.json", a.max_lado, dev)
    prueba = []
    if os.path.exists(os.path.join(a.carpeta, "transforms_test.json")):
        prueba, _ = leer_vistas(a.carpeta, "transforms_test.json", a.max_lado, dev)
    centros = torch.stack([torch.linalg.inv(v["viewmat"])[:3, 3] for v in vistas])
    escena = float((centros - centros.mean(0)).norm(dim=1).max()) * 1.1
    puntos, colores = leer_puntos(os.path.join(a.carpeta, ply or "puntos_iniciales.ply"))
    params, opt = iniciar(puntos, colores, a.sh, escena, dev)
    estrategia = DefaultStrategy(verbose=False, refine_stop_iter=int(a.pasos * 0.5), reset_every=3000)
    estrategia.check_sanity(params, opt)
    estado = estrategia.initialize_state(scene_scale=escena)
    decaer = torch.optim.lr_scheduler.ExponentialLR(opt["means"], gamma=0.01 ** (1.0 / a.pasos))
    print(f"{len(vistas)} vistas ({len(prueba)} de prueba) · {len(puntos):,} puntos iniciales · escena {escena:.1f} m", flush=True)

    def dibujar(v, paso):
        colores_sh = torch.cat([params["sh0"], params["shN"]], 1)
        img, alfa, info = rasterization(
            params["means"], F.normalize(params["quats"], dim=-1), torch.exp(params["scales"]),
            torch.sigmoid(params["opacities"]), colores_sh, v["viewmat"][None], v["K"][None], v["w"], v["h"],
            sh_degree=min(paso // 1000, a.sh), packed=False)
        return img[0], alfa[0], info

    t0 = time.time()
    orden = torch.randperm(len(vistas)).tolist()
    for paso in range(a.pasos):
        if not orden:
            orden = torch.randperm(len(vistas)).tolist()
        v = vistas[orden.pop()]
        img, alfa, info = dibujar(v, paso)
        estrategia.step_pre_backward(params, opt, estado, paso, info)
        gt = v["img"]
        gt_rgb = gt[..., :3] * gt[..., 3:]                   # premultiplicado: la salida de gsplat lo es
        l1 = (img - gt_rgb).abs().mean()
        d_ssim = 1 - ssim(img.permute(2, 0, 1)[None], gt_rgb.permute(2, 0, 1)[None])
        perdida = (1 - a.peso_ssim) * l1 + a.peso_ssim * d_ssim + a.peso_alfa * (alfa[..., 0] - gt[..., 3]).abs().mean()
        perdida.backward()
        estrategia.step_post_backward(params, opt, estado, paso, info, packed=False)
        for o in opt.values():
            o.step()
            o.zero_grad(set_to_none=True)
        decaer.step()
        if paso % 1000 == 0 or paso == a.pasos - 1:
            psnr = ""
            if prueba:
                with torch.no_grad():
                    vals = []
                    for p in prueba:
                        r, _, _ = dibujar(p, paso)
                        g = p["img"][..., :3] * p["img"][..., 3:]
                        vals.append(-10 * torch.log10(((r.clamp(0, 1) - g) ** 2).mean()))
                    psnr = f" · PSNR de prueba {torch.stack(vals).mean():.2f} dB"
            print(f"paso {paso:>6}/{a.pasos} · {len(params['means']):,} splats · pérdida {perdida.item():.4f}{psnr} · {time.time() - t0:.0f} s", flush=True)
    os.makedirs(os.path.dirname(os.path.abspath(a.salida)), exist_ok=True)
    exportar(params, a.salida)
    print(f"listo: {len(params['means']):,} splats → {a.salida}")


if __name__ == "__main__":
    main()
