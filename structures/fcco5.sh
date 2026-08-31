#!/bin/bash

#SBATCH -J fcco5
#SBATCH -t 01:00:00
#SBATCH -o /work/projects/Projects-da_tmm/Mian/structures/fcco5.output
#SBATCH -e /work/projects/Projects-da_tmm/Mian/structures/fcco5.error

$HOME/EMTO5.8/bmdl/bmdl < /work/projects/Projects-da_tmm/Mian/structures/fcco5.bmdl > /work/projects/Projects-da_tmm/Mian/structures/fcco5_bmdl.output
$HOME/EMTO5.8/kstr/kstr < /work/projects/Projects-da_tmm/Mian/structures/fcco5.kstr > /work/projects/Projects-da_tmm/Mian/structures/fcco5_kstr.output
$HOME/EMTO5.8/kstr/kstr < /work/projects/Projects-da_tmm/Mian/structures/fcco5M.kstr > /work/projects/Projects-da_tmm/Mian/structures/fcco5M_kstr.output
$HOME/EMTO5.8/shape/shape < /work/projects/Projects-da_tmm/Mian/structures/fcco5.shape > /work/projects/Projects-da_tmm/Mian/structures/fcco5_shape.output
