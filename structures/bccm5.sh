#!/bin/bash

#SBATCH -J bccm5
#SBATCH -t 01:00:00
#SBATCH -o /work/projects/Projects-da_tmm/Mian/structures/bccm5.output
#SBATCH -e /work/projects/Projects-da_tmm/Mian/structures/bccm5.error

$HOME/EMTO5.8/bmdl/bmdl < /work/projects/Projects-da_tmm/Mian/structures/bccm5.bmdl > /work/projects/Projects-da_tmm/Mian/structures/bccm5_bmdl.output
$HOME/EMTO5.8/kstr/kstr < /work/projects/Projects-da_tmm/Mian/structures/bccm5.kstr > /work/projects/Projects-da_tmm/Mian/structures/bccm5_kstr.output
$HOME/EMTO5.8/kstr/kstr < /work/projects/Projects-da_tmm/Mian/structures/bccm5M.kstr > /work/projects/Projects-da_tmm/Mian/structures/bccm5M_kstr.output
$HOME/EMTO5.8/shape/shape < /work/projects/Projects-da_tmm/Mian/structures/bccm5.shape > /work/projects/Projects-da_tmm/Mian/structures/bccm5_shape.output
