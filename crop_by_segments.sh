 input_file="/network/iss/lau-karachi/data_raw/Human/Nicolas_Tempier/POST_MORTEM/H5H/cryobloc/reged_slices/test_crop/H5H_cryobloc_bmreg_croped.nii"
 
param_1_crop=325-24
param_2_crop=0


 mrgrid "$input_file" crop \
        -axis 2 ${param_1_crop},${param_2_crop} \
        ${input_file}_croped_at_${param_1_crop}_${param_2_crop}.nii \
        -force -nthreads 70


input_file="/network/iss/lau-karachi/data_raw/Human/Nicolas_Tempier/POST_MORTEM/H5H/cryobloc/reged_slices/test_crop/H5H_cryobloc_bmreg_croped.nii"

param_1_crop_list=(291)
param_2_crop_list=(23) 

i=0
mrgrid "$input_file" crop \
    -axis 2 ${param_1_crop_list[$i]},${param_2_crop_list[$i]} \
    ${input_file}_croped_at_${param_1_crop_list[$i]}_${param_2_crop_list[$i]}.nii \
    -force -nthreads 7

mrinfo ${input_file}_croped_at_${param_1_crop_list[$i]}_${param_2_crop_list[$i]}.nii

input_file_cropped="${input_file}_croped_at_${param_1_crop_list[$i]}_${param_2_crop_list[$i]}.nii"
dimensions=$(mrinfo "$input_file_cropped" -size | awk '{print $3}')
mrgrid "$input_file_cropped" \
    regrid -size 1080,1050,$dimensions \
    "${input_file}_croped_at_${param_1_crop_list[$i]}_${param_2_crop_list[$i]}_resampled.nii" -nthreads 70 -force 


