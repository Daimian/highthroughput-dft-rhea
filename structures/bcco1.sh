#!/bin/bash

#SBATCH -J bcco1
#SBATCH -t 01:00:00
#SBATCH -o /work/projects/Projects-da_tmm/Mian/structures/bcco1.output
#SBATCH -e /work/projects/Projects-da_tmm/Mian/structures/bcco1.error

$HOME/EMTO5.8/bmdl/bmdl < /work/projects/Projects-da_tmm/Mian/structures/bcco1.bmdl > /work/projects/Projects-da_tmm/Mian/structures/bcco1_bmdl.output
$HOME/EMTO5.8/kstr/kstr < /work/projects/Projects-da_tmm/Mian/structures/bcco1.kstr > /work/projects/Projects-da_tmm/Mian/structures/bcco1_kstr.output
$HOME/EMTO5.8/kstr/kstr < /work/projects/Projects-da_tmm/Mian/structures/bcco1M.kstr > /work/projects/Projects-da_tmm/Mian/structures/bcco1M_kstr.output
$HOME/EMTO5.8/shape/shape < /work/projects/Projects-da_tmm/Mian/structures/bcco1.shape > /work/projects/Projects-da_tmm/Mian/structures/bcco1_shape.output
