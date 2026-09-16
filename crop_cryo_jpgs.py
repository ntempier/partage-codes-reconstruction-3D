import cv2
import os

# Dossiers source et destination
input_dir = "/network/iss/lau-karachi/data_raw/Human/Nicolas_Tempier/POST_MORTEM/H5H/cryobloc/renamed_pictures_gray"
output_dir = "/network/iss/lau-karachi/data_raw/Human/Nicolas_Tempier/POST_MORTEM/H5H/cryobloc/renamed_pictures_gray_croped"

# Créer le dossier de sortie s'il n'existe pas
os.makedirs(output_dir, exist_ok=True)

# Coordonnées du crop

x1, y1 = 1500, 1400
x2, y2 = 4600, 5300
# Lister et traiter toutes les images du dossier
for filename in os.listdir(input_dir):
    if filename.endswith(".JPG") and not filename.startswith("._"):
        input_path = os.path.join(input_dir, filename)
        output_path = os.path.join(output_dir, filename)
        
        # Charger l'image en niveaux de gris
        image = cv2.imread(input_path, cv2.IMREAD_GRAYSCALE)
        
        if image is None:
            print(f"Erreur : Impossible de charger {filename}")
            continue
        
        # Vérifier que le crop est possible
        if image.shape[0] < y2 or image.shape[1] < x2:
            print(f"Erreur : {filename} est trop petite pour être recadrée")
            continue
        
        # Recadrer l'image
        cropped_image = image[y1:y2, x1:x2]
        
        # Enregistrer l'image recadrée
        cv2.imwrite(output_path, cropped_image)
        print(f"Image enregistrée : {output_path}")

print("Traitement terminé.")
