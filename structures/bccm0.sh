#!/bin/bash

#SBATCH -J bccm0
#SBATCH -t 01:00:00
#SBATCH -o /work/projects/Projects-da_tmm/Mian/structures/bccm0.output
#SBATCH -e /work/projects/Projects-da_tmm/Mian/structures/bccm0.error

$HOME/EMTO5.8/bmdl/bmdl < /work/projects/Projects-da_tmm/Mian/structures/bccm0.bmdl > /work/projects/Projects-da_tmm/Mian/structures/bccm0_bmdl.output
$HOME/EMTO5.8/kstr/kstr < /work/projects/Projects-da_tmm/Mian/structures/bccm0.kstr > /work/projects/Projects-da_tmm/Mian/structures/bccm0_kstr.output
$HOME/EMTO5.8/kstr/kstr < /work/projects/Projects-da_tmm/Mian/structures/bccm0M.kstr > /work/projects/Projects-da_tmm/Mian/structures/bccm0M_kstr.output
$HOME/EMTO5.8/shape/shape < /work/projects/Projects-da_tmm/Mian/structures/bccm0.shape > /work/projects/Projects-da_tmm/Mian/structures/bccm0_shape.output
