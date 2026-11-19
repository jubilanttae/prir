from concurrent.futures import ProcessPoolExecutor
import math
import os
import time


def calculate_makespan(permutation, processing_times):
    n_machines = len(processing_times[0])
    times = [0] * n_machines
    for job in permutation:
        times[0] += processing_times[job][0]
        for m in range(1, n_machines):
            times[m] = max(times[m], times[m - 1]) + processing_times[job][m]
    return times[-1]


def run_neh(processing_times):
    n_jobs = len(processing_times)
    total_times = [(i, sum(processing_times[i])) for i in range(n_jobs)]
    total_times.sort(key=lambda x: x[1], reverse=True)

    current_seq = [total_times[0][0]]

    for i in range(1, n_jobs):
        job_to_insert = total_times[i][0]
        best_makespan = float("inf")
        best_seq = []

        for pos in range(len(current_seq) + 1):
            temp_seq = current_seq[:pos] + [job_to_insert] + current_seq[pos:]
            ms = calculate_makespan(temp_seq, processing_times)
            if ms < best_makespan:
                best_makespan = ms
                best_seq = temp_seq
        current_seq = best_seq

    return current_seq


def get_neighbors(permutation):
    neighbors = []
    n = len(permutation)
    for i in range(n):
        for j in range(i + 1, n):
            neighbor = list(permutation)
            neighbor[i], neighbor[j] = neighbor[j], neighbor[i]
            neighbors.append((neighbor, (i, j)))
    return neighbors


def run_tabu_search(processing_times, initial_sol, max_iter=100, tabu_tenure=7):
    start_time = time.time()
    best_sol = list(initial_sol)
    best_ms = calculate_makespan(best_sol, processing_times)
    best_time = 0.0
    current_sol = list(initial_sol)
    tabu_list = {}

    for iteration in range(max_iter):
        neighbors = get_neighbors(current_sol)
        best_neighbor = None
        best_neighbor_ms = float("inf")
        best_move = None

        for neighbor, move in neighbors:
            ms = calculate_makespan(neighbor, processing_times)
            is_tabu = move in tabu_list and tabu_list[move] > iteration

            if not is_tabu or ms < best_ms:
                if ms < best_neighbor_ms:
                    best_neighbor = neighbor
                    best_neighbor_ms = ms
                    best_move = move

        if best_neighbor is None:
            break

        current_sol = best_neighbor
        if best_neighbor_ms < best_ms:
            best_sol = list(best_neighbor)
            best_ms = best_neighbor_ms
            best_time = time.time() - start_time

        tabu_list[best_move] = iteration + tabu_tenure

    total_time = time.time() - start_time
    return best_sol, best_ms, best_time, total_time


def _evaluate_neighbor_chunk(args):
    chunk, processing_times, tabu_list, iteration, best_ms = args
    best_chunk_neighbor = None
    best_chunk_ms = float("inf")
    best_chunk_move = None

    for neighbor, move in chunk:
        ms = calculate_makespan(neighbor, processing_times)
        is_tabu = move in tabu_list and tabu_list[move] > iteration

        if not is_tabu or ms < best_ms:
            if ms < best_chunk_ms:
                best_chunk_neighbor = neighbor
                best_chunk_ms = ms
                best_chunk_move = move

    return best_chunk_neighbor, best_chunk_ms, best_chunk_move


def run_parallel_tabu_search(
    processing_times, initial_sol, max_iter=100, tabu_tenure=7, num_workers=None
):
    if num_workers is None:
        num_workers = os.cpu_count() or 4

    start_time = time.time()
    best_sol = list(initial_sol)
    best_ms = calculate_makespan(best_sol, processing_times)
    best_time = 0.0
    current_sol = list(initial_sol)
    tabu_list = {}

    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        for iteration in range(max_iter):
            neighbors = get_neighbors(current_sol)
            if not neighbors:
                break

            chunk_size = max(1, math.ceil(len(neighbors) / num_workers))
            chunks = [
                neighbors[i : i + chunk_size]
                for i in range(0, len(neighbors), chunk_size)
            ]
            tasks = [
                (chunk, processing_times, tabu_list, iteration, best_ms)
                for chunk in chunks
            ]

            best_neighbor = None
            best_neighbor_ms = float("inf")
            best_move = None

            for cand_neighbor, cand_ms, cand_move in executor.map(
                _evaluate_neighbor_chunk, tasks
            ):
                if cand_neighbor is not None and cand_ms < best_neighbor_ms:
                    best_neighbor = cand_neighbor
                    best_neighbor_ms = cand_ms
                    best_move = cand_move

            if best_neighbor is None:
                break

            current_sol = best_neighbor
            if best_neighbor_ms < best_ms:
                best_sol = list(best_neighbor)
                best_ms = best_neighbor_ms
                best_time = time.time() - start_time

            tabu_list[best_move] = iteration + tabu_tenure

    total_time = time.time() - start_time
    return best_sol, best_ms, best_time, total_time


def load_instances(file_path):
    with open(file_path, "r") as f:
        tokens = f.read().split()

    instances = []
    i = 0
    while i < len(tokens):
        if tokens[i].startswith("data."):
            name = tokens[i].replace(":", "")
            i += 1
            n = int(tokens[i])
            m = int(tokens[i + 1])
            i += 2

            processing_times = []
            for _ in range(n):
                row = []
                for _ in range(m):
                    row.append(int(tokens[i]))
                    i += 1
                processing_times.append(row)

            ref_ms = None
            if i < len(tokens) and tokens[i] == "neh:":
                i += 1
                ref_ms = int(tokens[i])
                i += 1
                while i < len(tokens) and not tokens[i].startswith("data."):
                    i += 1

            instances.append((name, processing_times, ref_ms))
        else:
            i += 1
    return instances


if __name__ == "__main__":
    file_path = "neh.data.txt"
    instances = load_instances(file_path)
    workers = os.cpu_count() or 4

    print(f"Liczba procesów roboczych: {workers}")
    print(
        f"{'Instance':<9} | {'Seq Cmax':<8} | {'Seq Time':<10} | {'Par Cmax':<8} | {'Par Time':<10} | {'Acceleration':<11}"
    )
    print("-" * 71)

    for name, processing_times, _ in instances:
        initial_sol = run_neh(processing_times)

        _, seq_ms, _, seq_total_time = run_tabu_search(
            processing_times, initial_sol
        )
        _, par_ms, _, par_total_time = run_parallel_tabu_search(
            processing_times, initial_sol, num_workers=workers
        )

        acceleration = (
            seq_total_time / par_total_time if par_total_time > 0 else 0.0
        )
        print(
            f"{name:<9} | {seq_ms:<8} | {seq_total_time:<10.5f} | {par_ms:<8} | {par_total_time:<10.5f} | {acceleration:<10.2f}x"
        )
