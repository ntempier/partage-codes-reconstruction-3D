base_dir="/network/iss/lau-karachi/data_raw/Human/Nicolas_Tempier/POST_MORTEM/H5H/cryobloc/reged_slices/test_crop/replaced_block/croped"

image_names=("0_65_resampled.nii" "66_resampled.nii" "67_287_resampled.nii" "288_290_resampled.nii" "291_301_resampled.nii" "302_325_resampled.nii")
template_image="/network/iss/lau-karachi/data_raw/Human/Nicolas_Tempier/POST_MORTEM/H5H/cryobloc/reged_slices/test_crop/not_replaced_blocks_3Dslicer/resampled/H5H_cryobloc_bmreg_croped.nii"
resampled_dir="/network/iss/lau-karachi/data_raw/Human/Nicolas_Tempier/POST_MORTEM/H5H/cryobloc/reged_slices/test_crop/replaced_block/croped/standardized"

for image_name in "${image_names[@]}"; do
    echo "Processing $image_name"
    mrgrid "${base_dir}/${image_name}" \
        regrid -template "$template_image" \
        "${resampled_dir}/${image_name}" -force -nthreads 70
done


mrgrid /network/iss/lau-karachi/data_raw/Human/Nicolas_Tempier/POST_MORTEM/H5H/cryobloc/reged_slices/test_crop/replaced_block/croped/standardized/66_resampled.nii regrid -template /network/iss/lau-karachi/data_raw/Human/Nicolas_Tempier/POST_MORTEM/H5H/cryobloc/reged_slices/test_crop/not_replaced_blocks_3Dslicer/resampled/H5H_cryobloc_bmreg_croped.nii /network/iss/lau-karachi/data_raw/Human/Nicolas_Tempier/POST_MORTEM/H5H/cryobloc/reged_slices/test_crop/replaced_block/croped/standardized/66_resampled2.nii -force -nthreads 70

