#!/bin/bash

#SBATCH -J bcco4
#SBATCH -t 01:00:00
#SBATCH -o /work/projects/Projects-da_tmm/Mian/structures/bcco4.output
#SBATCH -e /work/projects/Projects-da_tmm/Mian/structures/bcco4.error

$HOME/EMTO5.8/bmdl/bmdl < /work/projects/Projects-da_tmm/Mian/structures/bcco4.bmdl > /work/projects/Projects-da_tmm/Mian/structures/bcco4_bmdl.output
$HOME/EMTO5.8/kstr/kstr < /work/projects/Projects-da_tmm/Mian/structures/bcco4.kstr > /work/projects/Projects-da_tmm/Mian/structures/bcco4_kstr.output
$HOME/EMTO5.8/kstr/kstr < /work/projects/Projects-da_tmm/Mian/structures/bcco4M.kstr > /work/projects/Projects-da_tmm/Mian/structures/bcco4M_kstr.output
$HOME/EMTO5.8/shape/shape < /work/projects/Projects-da_tmm/Mian/structures/bcco4.shape > /work/projects/Projects-da_tmm/Mian/structures/bcco4_shape.output
