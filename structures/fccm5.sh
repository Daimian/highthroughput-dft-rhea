#!/bin/bash

#SBATCH -J fccm5
#SBATCH -t 01:00:00
#SBATCH -o /work/projects/Projects-da_tmm/Mian/structures/fccm5.output
#SBATCH -e /work/projects/Projects-da_tmm/Mian/structures/fccm5.error

$HOME/EMTO5.8/bmdl/bmdl < /work/projects/Projects-da_tmm/Mian/structures/fccm5.bmdl > /work/projects/Projects-da_tmm/Mian/structures/fccm5_bmdl.output
$HOME/EMTO5.8/kstr/kstr < /work/projects/Projects-da_tmm/Mian/structures/fccm5.kstr > /work/projects/Projects-da_tmm/Mian/structures/fccm5_kstr.output
$HOME/EMTO5.8/kstr/kstr < /work/projects/Projects-da_tmm/Mian/structures/fccm5M.kstr > /work/projects/Projects-da_tmm/Mian/structures/fccm5M_kstr.output
$HOME/EMTO5.8/shape/shape < /work/projects/Projects-da_tmm/Mian/structures/fccm5.shape > /work/projects/Projects-da_tmm/Mian/structures/fccm5_shape.output
