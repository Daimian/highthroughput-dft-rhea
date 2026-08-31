#!/bin/bash

#SBATCH -J fcco4
#SBATCH -t 01:00:00
#SBATCH -o /work/projects/Projects-da_tmm/Mian/structures/fcco4.output
#SBATCH -e /work/projects/Projects-da_tmm/Mian/structures/fcco4.error

$HOME/EMTO5.8/bmdl/bmdl < /work/projects/Projects-da_tmm/Mian/structures/fcco4.bmdl > /work/projects/Projects-da_tmm/Mian/structures/fcco4_bmdl.output
$HOME/EMTO5.8/kstr/kstr < /work/projects/Projects-da_tmm/Mian/structures/fcco4.kstr > /work/projects/Projects-da_tmm/Mian/structures/fcco4_kstr.output
$HOME/EMTO5.8/kstr/kstr < /work/projects/Projects-da_tmm/Mian/structures/fcco4M.kstr > /work/projects/Projects-da_tmm/Mian/structures/fcco4M_kstr.output
$HOME/EMTO5.8/shape/shape < /work/projects/Projects-da_tmm/Mian/structures/fcco4.shape > /work/projects/Projects-da_tmm/Mian/structures/fcco4_shape.output
