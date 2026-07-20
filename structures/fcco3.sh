#!/bin/bash

#SBATCH -J fcco3
#SBATCH -t 01:00:00
#SBATCH -o /work/projects/Projects-da_tmm/Mian/structures/fcco3.output
#SBATCH -e /work/projects/Projects-da_tmm/Mian/structures/fcco3.error

$HOME/EMTO5.8/bmdl/bmdl < /work/projects/Projects-da_tmm/Mian/structures/fcco3.bmdl > /work/projects/Projects-da_tmm/Mian/structures/fcco3_bmdl.output
$HOME/EMTO5.8/kstr/kstr < /work/projects/Projects-da_tmm/Mian/structures/fcco3.kstr > /work/projects/Projects-da_tmm/Mian/structures/fcco3_kstr.output
$HOME/EMTO5.8/kstr/kstr < /work/projects/Projects-da_tmm/Mian/structures/fcco3M.kstr > /work/projects/Projects-da_tmm/Mian/structures/fcco3M_kstr.output
$HOME/EMTO5.8/shape/shape < /work/projects/Projects-da_tmm/Mian/structures/fcco3.shape > /work/projects/Projects-da_tmm/Mian/structures/fcco3_shape.output
