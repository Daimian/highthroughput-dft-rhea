import os
import csv
import numpy as np
import pyemto
from config import ELEMENTS, EMTO_PARAMS


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


def _params_with_efgs(efgs):
    """EMTO_PARAMS 加上逐合金的 efgs。efgs 为 None 时沿用 pyemto 默认值。"""
    params = dict(EMTO_PARAMS)
    if efgs is not None:
        params['efgs'] = efgs
    return params


def generate_eos_inputs(alloy_id, atoms, concs, sws_list, stage_dir, latpath,
                        efgs=None):
    folder = os.path.join(stage_dir, alloy_id)
    os.makedirs(folder, exist_ok=True)

    concs_frac = [c / 100.0 for c in concs]
    splts = [0.0] * len(atoms)
    params = _params_with_efgs(efgs)

    system = pyemto.System(folder=folder)
    system.bulk(
        jobname=alloy_id,
        latpath=latpath,
        atoms=atoms,
        concs=concs_frac,
        splts=splts,
        sws=sws_list[0],
        **params,
    )
    system.lattice_constants_batch_generate(sws=sws_list)


def generate_elastic_inputs(alloy_id, atoms, concs, sws0, stage_dir, latpath,
                            efgs=None):
    folder = os.path.join(stage_dir, alloy_id)
    os.makedirs(folder, exist_ok=True)

    concs_frac = [c / 100.0 for c in concs]
    splts = [0.0] * len(atoms)
    params = _params_with_efgs(efgs)

    system = pyemto.System(folder=folder)
    system.bulk(
        jobname=alloy_id,
        latpath=latpath,
        atoms=atoms,
        concs=concs_frac,
        splts=splts,
        sws=sws0,
        **params,
    )
    system.elastic_constants_batch_generate(sws=sws0)
