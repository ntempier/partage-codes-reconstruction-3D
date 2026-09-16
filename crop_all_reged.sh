#!/bin/bash

input_dir="/network/iss/lau-karachi/data_raw/Human/Nicolas_Tempier/POST_MORTEM/H5H/cryobloc/reged_slices/ants"
output_dir="/network/iss/lau-karachi/data_raw/Human/Nicolas_Tempier/POST_MORTEM/H5H/cryobloc/reged_slices/test_crop/croped"

for input_file in "$input_dir"/*.nii; do
    if [[ "$input_file" == *.nii.gz ]]; then
        continue
    fi
    filename=$(basename "$input_file")
    output_file="$output_dir/$filename"
    
    mrgrid "$input_file" crop \
        -axis 0 1400,1000 \
        -axis 1 50,700 \
        "$output_file" \
        -force -nthreads 70
done


mrcat /network/iss/lau-karachi/data_raw/Human/Nicolas_Tempier/POST_MORTEM/H5H/cryobloc/reged_slices/test_crop/croped/*.nii \
    /network/iss/lau-karachi/data_raw/Human/Nicolas_Tempier/POST_MORTEM/H5H/cryobloc/reged_slices/test_crop/H5H_cryobloc_bmreg_croped.nii -axis 2 -force -nthreads 70



mrgrid '/network/iss/lau-karachi/data_raw/Human/Nicolas_Tempier/POST_MORTEM/H5H/cryobloc/H5H_cryobloc_bmreg_croped.nii' \
    regrid -size 1080,1050,325 -interp cubic \
    '/network/iss/lau-karachi/data_raw/Human/Nicolas_Tempier/POST_MORTEM/H5H/cryobloc/reged_slices/test_crop/H5H_cryobloc_bmreg_croped_resampled.nii' -nthreads 70    -force

