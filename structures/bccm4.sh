#!/bin/bash

#SBATCH -J bccm4
#SBATCH -t 01:00:00
#SBATCH -o /work/projects/Projects-da_tmm/Mian/structures/bccm4.output
#SBATCH -e /work/projects/Projects-da_tmm/Mian/structures/bccm4.error

$HOME/EMTO5.8/bmdl/bmdl < /work/projects/Projects-da_tmm/Mian/structures/bccm4.bmdl > /work/projects/Projects-da_tmm/Mian/structures/bccm4_bmdl.output
$HOME/EMTO5.8/kstr/kstr < /work/projects/Projects-da_tmm/Mian/structures/bccm4.kstr > /work/projects/Projects-da_tmm/Mian/structures/bccm4_kstr.output
$HOME/EMTO5.8/kstr/kstr < /work/projects/Projects-da_tmm/Mian/structures/bccm4M.kstr > /work/projects/Projects-da_tmm/Mian/structures/bccm4M_kstr.output
$HOME/EMTO5.8/shape/shape < /work/projects/Projects-da_tmm/Mian/structures/bccm4.shape > /work/projects/Projects-da_tmm/Mian/structures/bccm4_shape.output
