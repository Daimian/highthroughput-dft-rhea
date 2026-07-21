import os
import csv
import numpy as np
import pyemto
from config import ELEMENTS, EMTO_PARAMS, DEPTH_OVERRIDES
from efgs import calc_efgs


def _params_for(alloy_id):
    """EMTO_PARAMS with a per-alloy depth override applied (see
    config.DEPTH_OVERRIDES). Returns a fresh dict so EMTO_PARAMS is untouched."""
    params = dict(EMTO_PARAMS)
    if alloy_id in DEPTH_OVERRIDES:
        params['depth'] = DEPTH_OVERRIDES[alloy_id]
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
        **_params_for(alloy_id),
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
        **_params_for(alloy_id),
    )

    if composition is not None:
        system.emto.set_values(efgs=calc_efgs(composition, sws0))
    system.elastic_constants_batch_generate(sws=sws0)
