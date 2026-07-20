#!/bin/bash

#SBATCH -J fcco1
#SBATCH -t 01:00:00
#SBATCH -o /work/projects/Projects-da_tmm/Mian/structures/fcco1.output
#SBATCH -e /work/projects/Projects-da_tmm/Mian/structures/fcco1.error

$HOME/EMTO5.8/bmdl/bmdl < /work/projects/Projects-da_tmm/Mian/structures/fcco1.bmdl > /work/projects/Projects-da_tmm/Mian/structures/fcco1_bmdl.output
$HOME/EMTO5.8/kstr/kstr < /work/projects/Projects-da_tmm/Mian/structures/fcco1.kstr > /work/projects/Projects-da_tmm/Mian/structures/fcco1_kstr.output
$HOME/EMTO5.8/kstr/kstr < /work/projects/Projects-da_tmm/Mian/structures/fcco1M.kstr > /work/projects/Projects-da_tmm/Mian/structures/fcco1M_kstr.output
$HOME/EMTO5.8/shape/shape < /work/projects/Projects-da_tmm/Mian/structures/fcco1.shape > /work/projects/Projects-da_tmm/Mian/structures/fcco1_shape.output
