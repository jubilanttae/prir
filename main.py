import math
import sys
import time
from multiprocessing import Pool

import numpy as np
from PIL import Image


def split_image(image, n_parts, overlap=1):
    arr = np.array(image.convert("L"), dtype=np.float32)
    height = arr.shape[0]
    bounds = np.linspace(0, height, n_parts + 1, dtype=int)
    fragments = []
    for i in range(n_parts):
        start = bounds[i]
        end = bounds[i + 1]
        top = max(0, start - overlap)
        bottom = min(height, end + overlap)
        fragments.append((arr[top:bottom], start - top, end - start))
    return fragments


def edge_filter(fragment):
    arr, offset, rows = fragment
    h, w = arr.shape
    p = np.pad(arr, 1, mode="edge").tolist()
    out = [[0.0] * w for _ in range(h)]
    for y in range(h):
        r0 = p[y]
        r1 = p[y + 1]
        r2 = p[y + 2]
        row = out[y]
        for x in range(w):
            gx = (r0[x + 2] - r0[x]) + 2 * (r1[x + 2] - r1[x]) + (r2[x + 2] - r2[x])
            gy = (r2[x] - r0[x]) + 2 * (r2[x + 1] - r0[x + 1]) + (r2[x + 2] - r0[x + 2])
            row[x] = math.sqrt(gx * gx + gy * gy)
    result = np.array(out, dtype=np.float32)
    return result[offset:offset + rows]


def merge_image(fragments):
    merged = np.vstack(fragments)
    max_value = merged.max()
    if max_value > 0:
        merged = merged / max_value * 255.0
    return Image.fromarray(merged.astype(np.uint8))


def process_parallel(image, pool, n_processes):
    fragments = split_image(image, n_processes)
    results = pool.map(edge_filter, fragments)
    return merge_image(results)


def process_sequential(image):
    fragments = split_image(image, 1)
    return merge_image([edge_filter(fragments[0])])


def main():
    image_path = sys.argv[1] if len(sys.argv) > 1 else "in1.jpg"
    n_processes = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    output_path = sys.argv[3] if len(sys.argv) > 3 else "processed_image.png"

    image = Image.open(image_path)

    with Pool(n_processes) as pool:
        pool.map(math.sqrt, range(n_processes))

        start = time.perf_counter()
        process_sequential(image)
        sequential_time = time.perf_counter() - start

        start = time.perf_counter()
        result = process_parallel(image, pool, n_processes)
        parallel_time = time.perf_counter() - start

    result.save(output_path)

    print(f"Czas sekwencyjny: {sequential_time:.3f} s")
    print(f"Czas rownolegly ({n_processes} procesow): {parallel_time:.3f} s")
    print(f"Przyspieszenie: {sequential_time / parallel_time:.2f}x")


if __name__ == "__main__":
    main()
