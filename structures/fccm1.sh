#!/bin/bash

#SBATCH -J fccm1
#SBATCH -t 01:00:00
#SBATCH -o /work/projects/Projects-da_tmm/Mian/structures/fccm1.output
#SBATCH -e /work/projects/Projects-da_tmm/Mian/structures/fccm1.error

$HOME/EMTO5.8/bmdl/bmdl < /work/projects/Projects-da_tmm/Mian/structures/fccm1.bmdl > /work/projects/Projects-da_tmm/Mian/structures/fccm1_bmdl.output
$HOME/EMTO5.8/kstr/kstr < /work/projects/Projects-da_tmm/Mian/structures/fccm1.kstr > /work/projects/Projects-da_tmm/Mian/structures/fccm1_kstr.output
$HOME/EMTO5.8/kstr/kstr < /work/projects/Projects-da_tmm/Mian/structures/fccm1M.kstr > /work/projects/Projects-da_tmm/Mian/structures/fccm1M_kstr.output
$HOME/EMTO5.8/shape/shape < /work/projects/Projects-da_tmm/Mian/structures/fccm1.shape > /work/projects/Projects-da_tmm/Mian/structures/fccm1_shape.output
