import os
import csv
import numpy as np
import pyemto
from config import (ELEMENTS, EMTO_PARAMS, DEEP_TA_THRESHOLD, DEEP_TA_DEPTH,
                    DEEP_TA_AMIX, DEEP_TA_ALLOYS, AMIX_ONLY_ALLOYS,
                    MIXED_HF_DEPTH, MIXED_HF_ALLOYS)
from efgs import calc_efgs


def _params_for(alloy_id, composition):
    """EMTO_PARAMS with a convergence override, needed to keep the SCF in the
    ground electronic state. Three tiers (checked in order):

    - full override (depth 0.80 + AMIX 0.02): Ta >= DEEP_TA_THRESHOLD or listed
      in DEEP_TA_ALLOYS (Ta-rich, and no-Hf Ta 1-29). depth is NOT energy-neutral
      (it shifts c'), so these use depth 0.80 in every stage (stage2 recomputed).
    - mixed-depth Hf (depth 0.90 + AMIX 0.02): listed in MIXED_HF_ALLOYS (Hf-bearing
      Ta 1-29). depth 0.90 is the deepest that still converges the symmetry-broken
      distortions; their depth-0.95 stage2 B0 is KEPT (do NOT regenerate stage2 --
      depth<=0.90 corrupts the Hf EOS). So c' @0.90 pairs with B0 @0.95.
    - AMIX-only (AMIX 0.02, depth 0.95): listed in AMIX_ONLY_ALLOYS (no-Ta). AMIX is
      energy-neutral, so these keep depth 0.95 and their depth-0.95 stage2 B0.

    Earlier tiers win if an alloy is in more than one list. Returns a fresh dict so
    EMTO_PARAMS is untouched. composition is {element: at%}; None keeps defaults."""
    params = dict(EMTO_PARAMS)
    ta = composition.get('Ta', 0) if composition else 0
    if ta >= DEEP_TA_THRESHOLD or alloy_id in DEEP_TA_ALLOYS:
        params['depth'] = DEEP_TA_DEPTH
        params['amix'] = DEEP_TA_AMIX
    elif alloy_id in MIXED_HF_ALLOYS:
        params['depth'] = MIXED_HF_DEPTH
        params['amix'] = DEEP_TA_AMIX
    elif alloy_id in AMIX_ONLY_ALLOYS:
        params['amix'] = DEEP_TA_AMIX
    return params


def parse_csv(csv_path):
    alloys = []
    with open(csv_path, newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            atoms = []
            concs = []
            composition = {}
            for elem in ELEMENTS:
                c = int(row[elem])
                if c > 0:
                    atoms.append(elem)
                    concs.append(c)
                    composition[elem] = c
            alloys.append({
                'id': row['DFT_ID'],
                'alloy': row['Alloy'],
                'atoms': atoms,
                'concs': concs,
                'composition': composition,
            })
    return alloys


def generate_eos_inputs(alloy_id, atoms, concs, sws_list, stage_dir, latpath,
                        composition=None):
    """生成一个合金的 EOS 输入。

    EFGS 逐点按体积设置（见 efgs.calc_efgs）：pyemto 的 batch_generate 对所有点
    复用同一个 EFGS，所以给定 composition 时改为每个 sws 单独设 EFGS 再各自生成。
    composition 为 None 时（仅测试/无成分信息）沿用 pyemto 默认 EFGS。
    """
    folder = os.path.join(stage_dir, alloy_id)
    os.makedirs(folder, exist_ok=True)

    concs_frac = [c / 100.0 for c in concs]
    splts = [0.0] * len(atoms)

    system = pyemto.System(folder=folder)
    system.bulk(
        jobname=alloy_id,
        latpath=latpath,
        atoms=atoms,
        concs=concs_frac,
        splts=splts,
        sws=sws_list[0],
        **_params_for(alloy_id, composition),
    )

    if composition is None:
        system.lattice_constants_batch_generate(sws=sws_list)
    else:
        for sws in sws_list:
            system.emto.set_values(efgs=calc_efgs(composition, sws))
            system.lattice_constants_batch_generate(sws=[sws])


def generate_elastic_inputs(alloy_id, atoms, concs, sws0, stage_dir, latpath,
                            composition=None):
    """生成一个合金在 sws0 处的弹性常数输入。所有畸变结构同体积，共用一个 EFGS。"""
    folder = os.path.join(stage_dir, alloy_id)
    os.makedirs(folder, exist_ok=True)

    concs_frac = [c / 100.0 for c in concs]
    splts = [0.0] * len(atoms)

    system = pyemto.System(folder=folder)
    system.bulk(
        jobname=alloy_id,
        latpath=latpath,
        atoms=atoms,
        concs=concs_frac,
        splts=splts,
        sws=sws0,
        **_params_for(alloy_id, composition),
    )

    if composition is not None:
        system.emto.set_values(efgs=calc_efgs(composition, sws0))
    system.elastic_constants_batch_generate(sws=sws0)
