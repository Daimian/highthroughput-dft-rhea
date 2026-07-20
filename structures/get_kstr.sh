### Run kstr, bmdl, and shape 

# for i in bccm*.kstr ; do echo $i ; kstr < $i ; done
# for i in bccm*.bmdl ; do echo $i ; bmdl < $i ; done 
# for i in bccm*.shape ; do echo $i ; shape < $i ; done 

# for i in bcco*.kstr ; do echo $i ; kstr < $i ; done
# for i in bcco*.bmdl ; do echo $i ; bmdl < $i ; done 
# for i in bcco*.shape ; do echo $i ; shape < $i ; done

# for i in fccm*.kstr ; do echo $i ; kstr < $i ; done
# for i in fccm*.bmdl ; do echo $i ; bmdl < $i ; done 
# for i in fccm*.shape ; do echo $i ; shape < $i ; done 

for i in fcco*.kstr ; do echo $i ; kstr < $i ; done
for i in fcco*.bmdl ; do echo $i ; bmdl < $i ; done 
for i in fcco*.shape ; do echo $i ; shape < $i ; done 