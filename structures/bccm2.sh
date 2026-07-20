#!/bin/bash

#SBATCH -J bccm2
#SBATCH -t 01:00:00
#SBATCH -o /work/projects/Projects-da_tmm/Mian/structures/bccm2.output
#SBATCH -e /work/projects/Projects-da_tmm/Mian/structures/bccm2.error

$HOME/EMTO5.8/bmdl/bmdl < /work/projects/Projects-da_tmm/Mian/structures/bccm2.bmdl > /work/projects/Projects-da_tmm/Mian/structures/bccm2_bmdl.output
$HOME/EMTO5.8/kstr/kstr < /work/projects/Projects-da_tmm/Mian/structures/bccm2.kstr > /work/projects/Projects-da_tmm/Mian/structures/bccm2_kstr.output
$HOME/EMTO5.8/kstr/kstr < /work/projects/Projects-da_tmm/Mian/structures/bccm2M.kstr > /work/projects/Projects-da_tmm/Mian/structures/bccm2M_kstr.output
$HOME/EMTO5.8/shape/shape < /work/projects/Projects-da_tmm/Mian/structures/bccm2.shape > /work/projects/Projects-da_tmm/Mian/structures/bccm2_shape.output
