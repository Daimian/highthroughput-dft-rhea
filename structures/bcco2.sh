#!/bin/bash

#SBATCH -J bcco2
#SBATCH -t 01:00:00
#SBATCH -o /work/projects/Projects-da_tmm/Mian/structures/bcco2.output
#SBATCH -e /work/projects/Projects-da_tmm/Mian/structures/bcco2.error

$HOME/EMTO5.8/bmdl/bmdl < /work/projects/Projects-da_tmm/Mian/structures/bcco2.bmdl > /work/projects/Projects-da_tmm/Mian/structures/bcco2_bmdl.output
$HOME/EMTO5.8/kstr/kstr < /work/projects/Projects-da_tmm/Mian/structures/bcco2.kstr > /work/projects/Projects-da_tmm/Mian/structures/bcco2_kstr.output
$HOME/EMTO5.8/kstr/kstr < /work/projects/Projects-da_tmm/Mian/structures/bcco2M.kstr > /work/projects/Projects-da_tmm/Mian/structures/bcco2M_kstr.output
$HOME/EMTO5.8/shape/shape < /work/projects/Projects-da_tmm/Mian/structures/bcco2.shape > /work/projects/Projects-da_tmm/Mian/structures/bcco2_shape.output
