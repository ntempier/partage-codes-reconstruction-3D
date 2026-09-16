res_dir="/network/iss/lau-karachi/data_raw/Human/Nicolas_Tempier/POST_MORTEM/H5H/cryobloc/reg_2_dti/bm_reg" 
mkdir -p $res_dir

# Étape 1: Recalage Rigide
blockmatching \
-reference /network/iss/lau-karachi/data_raw/Human/Nicolas_Tempier/POST_MORTEM/H5H/raw_datas/b10000_b0_3d.nii \
-floating "/network/iss/lau-karachi/data_raw/Human/Nicolas_Tempier/POST_MORTEM/H5H/cryobloc/reg_2_dti/H5H_Cryobloc_noice.nii" \
-result $res_dir/H5H_Cryo_in_DWIresult_rigid.nii \
-result-transformation $res_dir/H5H_Cryo_in_DWIresult_transformation_rigid.trsf \
-transformation-type rigid3D \
-similarity-measure ecc \
-parallel 

# Étape 2: Recalage de Similitude
blockmatching \
-reference /network/iss/lau-karachi/data_raw/Human/Nicolas_Tempier/POST_MORTEM/H5H/raw_datas/b10000_b0_3d.nii \
-floating "/network/iss/lau-karachi/data_raw/Human/Nicolas_Tempier/POST_MORTEM/H5H/cryobloc/reg_2_dti/H5H_Cryobloc_noice.nii" \
-initial-transformation $res_dir/H5H_Cryo_in_DWIresult_transformation_rigid.trsf \
-result $res_dir/H5H_Cryo_in_DWIresult_similitude.nii \
-result-transformation $res_dir/H5H_Cryo_in_DWIresult_transformation_similitude.trsf \
-transformation-type similitude3D \
-similarity-measure ecc \
-composition-with-initial \
-parallel

# Étape 3: Recalage Affine
blockmatching \
-reference /network/iss/lau-karachi/data_raw/Human/Nicolas_Tempier/POST_MORTEM/H5H/raw_datas/b10000_b0_3d.nii \
-floating "/network/iss/lau-karachi/data_raw/Human/Nicolas_Tempier/POST_MORTEM/H5H/cryobloc/reg_2_dti/H5H_Cryobloc_noice.nii" \
-initial-transformation $res_dir/H5H_Cryo_in_DWIresult_transformation_similitude.trsf \
-result $res_dir/H5H_Cryo_in_DWIresult_affine.nii \
-result-transformation $res_dir/H5H_Cryo_in_DWIresult_transformation_affine.trsf \
-transformation-type affine3D \
-similarity-measure ecc \
-composition-with-initial \
-parallel

# Étape 4: Recalage Non-Rigide
blockmatching \
-reference /network/iss/lau-karachi/data_raw/Human/Nicolas_Tempier/POST_MORTEM/H5H/raw_datas/b10000_b0_3d.nii \
-floating "/network/iss/lau-karachi/data_raw/Human/Nicolas_Tempier/POST_MORTEM/H5H/cryobloc/reg_2_dti/H5H_Cryobloc_noice.nii" \
-initial-transformation $res_dir/H5H_Cryo_in_DWIresult_transformation_similitude.trsf \
-result $res_dir/H5H_Cryo_in_DWIresult_vectorfield3D.nii \
-result-transformation $res_dir/H5H_Cryo_in_DWIresult_transformation_vectorfield3D.trsf \
-transformation-type vectorfield3D \
-similarity-measure ecc \
-composition-with-initial \
-parallel

