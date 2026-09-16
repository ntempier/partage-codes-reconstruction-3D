# Partage codes reconstruction 3D

Codes pour la reconstruction d'un bloc 3D (cryobloc) à partir des photographies
prises tranche par tranche au cryotome (projet H5H, POST_MORTEM).

Ce dépôt ne contient **que le code** (scripts Python / Bash / configs JSON) — les
images, volumes NIfTI et autres données brutes ne sont pas inclus (trop volumineux,
et propres au partage interne).

## Étapes du pipeline

Le pipeline complet enchaîne les étapes suivantes. Deux générations de scripts sont
présentes : une version simple (première implémentation) et une version plus robuste
utilisée en dernier (recalage "middle-out" avec exclusion des coupes défectueuses).

1. **Tri / renommage des photos**
   - `rename_pictures_ordered.py`, `rename_pictures_ordered.sh`

2. **Conversion en niveaux de gris**
   - `color_2_gray.py`

3. **Crop**
   - Version simple : `where_2_crop.py` (prévisualisation des coordonnées), `crop_cryo_jpgs.py` (crop fixe)
   - Version robuste : `choose_crop_interface.py` (interface interactive d'échantillonnage du crop sur plusieurs coupes) puis `apply_crop_config.py` (interpolation du crop entre les points échantillonnés, gère le déplacement du bloc au fil des coupes)
   - Configs générées : `crop_selection/crop_config.json`, `crop_selection/crop_interpolated_all.json`

4. **Conversion en NIfTI / mise sur grille commune**
   - Version simple : `convert_2_nifti.py`, `cryobloc_from_JPGs.py`, `3D_raw_cryobloc_2_2D_niftis.py`
   - Version robuste : `jpgs_to_nifti_slices.py` (une slice NIfTI 2D par image, grille/affine commune), `prepare_ants_nifti_slices.py`

5. **Recalage deux à deux (pairwise)**
   - Version simple, propagation séquentielle : `register_slice_per_slice.sh`, `register_slice_by_slice_ants_flirt_blockmatching.sh`, `run_cropped_blockmatching_registration.sh`, `circular_registration/`
   - Version robuste, "middle-out" à partir d'une coupe centrale avec exclusion des coupes défectueuses : `run_filtered_ants_recalage.py`, `run_cropped_ants_affine_middleout.sh`, `run_cropped_blockmatching_affine_middleout.sh`, `fix_filtered_registration_boundary.py` (correction des artefacts de bord entre lots)

6. **Re-reconstruction du volume 3D**
   - Version simple : `reconstruct_3D_nifti_from_niftis.py`, `recontruction_volume_3D_from_2D_niftis.py`
   - Version robuste : `reconstruct_filtered_registered_cryobloc.py`, `stack_registered_slices_to_nifti.py`, `reconstruct_cropped_cryobloc_downsampled.py`, `make_registered_mpr_preview.py` (génère aussi des previews MPR et montages de contrôle)

### Autres scripts utilitaires
- `crop_roi_niftis.py`, `crop_all_reged.sh`, `crop_by_segments.sh`, `preview_crop_dimensions.py` — variantes de crop sur les NIfTI déjà générés
- `extract_cryobloc_slices_in_volume_space.py` — extraction de coupes dans l'espace du volume
- `remove_ice/split_nifti_z_slices_preserve_affine.py` — séparation de slices en conservant l'affine
- `reg_2_dti/bm_reg_cryo_2_dti.sh` — recalage du cryobloc vers la DTI

## Flux recommandé (version robuste)

```
choose_crop_interface.py
  -> apply_crop_config.py
  -> jpgs_to_nifti_slices.py
  -> run_filtered_ants_recalage.py   (+ fix_filtered_registration_boundary.py si besoin)
  -> reconstruct_filtered_registered_cryobloc.py
```

## Dépendances

Python : `nibabel`, `numpy`, `Pillow`, `opencv-python` (`cv2`), `matplotlib`
Externes : [ANTs](https://github.com/ANTsX/ANTs) (`antsRegistration`, `antsApplyTransforms`), `blockmatching` (BioEmergences / baladin)

## Remarque

Les chemins codés en dur dans certains scripts (`/network/iss/lau-karachi/...`) font
référence au stockage interne du laboratoire et devront être adaptés pour toute
utilisation en dehors de cet environnement.
