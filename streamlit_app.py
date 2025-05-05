import streamlit as st
import pandas as pd

# Titre de l'application
st.title("Créateur de Recettes")

# Champs pour entrer les informations de la recette
nom = st.text_input("Nom de la recette")
ingredients = st.text_area("Ingrédients (séparés par des virgules)")
instructions = st.text_area("Instructions")

# Bouton pour sauvegarder
if st.button("Sauvegarder la recette"):
    recette = {
        "Nom": nom,
        "Ingrédients": ingredients,
        "Instructions": instructions
    }
    try:
        # Charger ou créer un fichier Excel
        try:
            df = pd.read_excel("recettes.xlsx")
        except FileNotFoundError:
            df = pd.DataFrame(columns=["Nom", "Ingrédients", "Instructions"])
        
        # Ajouter la nouvelle recette
        df = df.append(recette, ignore_index=True)
        df.to_excel("recettes.xlsx", index=False)
        st.success(f"Recette '{nom}' sauvegardée avec succès !")
    except Exception as e:
        st.error(f"Erreur lors de la sauvegarde : {e}")