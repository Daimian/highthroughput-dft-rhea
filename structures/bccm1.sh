#!/bin/bash

#SBATCH -J bccm1
#SBATCH -t 01:00:00
#SBATCH -o /work/projects/Projects-da_tmm/Mian/structures/bccm1.output
#SBATCH -e /work/projects/Projects-da_tmm/Mian/structures/bccm1.error

$HOME/EMTO5.8/bmdl/bmdl < /work/projects/Projects-da_tmm/Mian/structures/bccm1.bmdl > /work/projects/Projects-da_tmm/Mian/structures/bccm1_bmdl.output
$HOME/EMTO5.8/kstr/kstr < /work/projects/Projects-da_tmm/Mian/structures/bccm1.kstr > /work/projects/Projects-da_tmm/Mian/structures/bccm1_kstr.output
$HOME/EMTO5.8/kstr/kstr < /work/projects/Projects-da_tmm/Mian/structures/bccm1M.kstr > /work/projects/Projects-da_tmm/Mian/structures/bccm1M_kstr.output
$HOME/EMTO5.8/shape/shape < /work/projects/Projects-da_tmm/Mian/structures/bccm1.shape > /work/projects/Projects-da_tmm/Mian/structures/bccm1_shape.output
