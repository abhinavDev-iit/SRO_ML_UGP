#!/usr/bin/env bash

# Run the four prepared Phase 7 static SCFs sequentially under QE 7.x.
# Existing completed outputs are reused; incomplete outputs are preserved with
# a timestamp before a retry. The script never deletes prior outputs.

set -u

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
CONDA_EXE="/home/aditya/miniconda3/bin/conda"
CONDA_ENV="qe7"
FIDS=(gra62121526 gra62121527 gra64001864 gra62121595)
PSEUDOS=(Co_pbe_v1.2.uspp.F.UPF cr_pbe_v1.5.uspp.F.UPF)

run_one() {
    local fid="$1"
    local input="${REPO_ROOT}/dft_inputs/production/${fid}/scf.in"
    local run_dir="${REPO_ROOT}/dft_runs/${fid}"
    local output="${run_dir}/scf.out"
    local pseudo source archived exit_code

    printf '\nRUNNING %s\n' "${fid}"

    if [[ ! -f "${input}" ]]; then
        printf 'FAILED %s: missing input %s\n' "${fid}" "${input}"
        return 1
    fi

    mkdir -p "${run_dir}/scratch" "${run_dir}/pseudopotentials"
    cp "${input}" "${run_dir}/scf.in"

    for pseudo in "${PSEUDOS[@]}"; do
        source="${REPO_ROOT}/dft_pseudos/${pseudo}"
        if [[ ! -f "${source}" ]]; then
            printf 'FAILED %s: missing pseudopotential %s\n' "${fid}" "${source}"
            return 1
        fi
        if [[ ! -f "${run_dir}/pseudopotentials/${pseudo}" ]]; then
            cp "${source}" "${run_dir}/pseudopotentials/${pseudo}"
        fi
    done

    if [[ -f "${output}" ]] && grep -q 'JOB DONE\.' "${output}"; then
        printf 'SUCCESS %s: existing output contains JOB DONE\n' "${fid}"
        return 0
    fi

    if [[ -f "${output}" ]]; then
        archived="${run_dir}/scf.previous.$(date -u +%Y%m%dT%H%M%SZ).out"
        mv "${output}" "${archived}"
        printf 'Preserved prior incomplete output as %s\n' "${archived}"
    fi

    (
        cd "${run_dir}" || exit 1
        "${CONDA_EXE}" run --no-capture-output -n "${CONDA_ENV}" pw.x -in scf.in > scf.out 2>&1
    )
    exit_code=$?

    if [[ -f "${output}" ]] && grep -q 'JOB DONE\.' "${output}"; then
        printf 'SUCCESS %s\n' "${fid}"
        return 0
    fi

    printf 'FAILED %s: QE exit code %s; inspect %s\n' "${fid}" "${exit_code}" "${output}"
    return 1
}

failures=0
for fid in "${FIDS[@]}"; do
    if ! run_one "${fid}"; then
        failures=$((failures + 1))
    fi
done

if (( failures == 0 )); then
    printf '\nAll four SCFs completed successfully.\n'
    exit 0
fi

printf '\nCompleted with %s failed SCF calculation(s).\n' "${failures}"
exit 1
