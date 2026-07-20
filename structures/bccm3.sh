#!/bin/bash

#SBATCH -J bccm3
#SBATCH -t 01:00:00
#SBATCH -o /work/projects/Projects-da_tmm/Mian/structures/bccm3.output
#SBATCH -e /work/projects/Projects-da_tmm/Mian/structures/bccm3.error

$HOME/EMTO5.8/bmdl/bmdl < /work/projects/Projects-da_tmm/Mian/structures/bccm3.bmdl > /work/projects/Projects-da_tmm/Mian/structures/bccm3_bmdl.output
$HOME/EMTO5.8/kstr/kstr < /work/projects/Projects-da_tmm/Mian/structures/bccm3.kstr > /work/projects/Projects-da_tmm/Mian/structures/bccm3_kstr.output
$HOME/EMTO5.8/kstr/kstr < /work/projects/Projects-da_tmm/Mian/structures/bccm3M.kstr > /work/projects/Projects-da_tmm/Mian/structures/bccm3M_kstr.output
$HOME/EMTO5.8/shape/shape < /work/projects/Projects-da_tmm/Mian/structures/bccm3.shape > /work/projects/Projects-da_tmm/Mian/structures/bccm3_shape.output
