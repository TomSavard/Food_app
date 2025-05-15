import streamlit as st

def run(drive, folder_id):
    st.title("Weekly Menu Planner")

    # Initialize week menu in session state if not present
    if "week_menu" not in st.session_state:
        st.session_state.week_menu = {day: None for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]}

    # Get all recipes
    recipes = st.session_state.recipes

    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    for day in days:
        st.subheader(day)
        recipe_names = [r.name for r in recipes]
        current = st.session_state.week_menu.get(day)
        selected = st.selectbox(
            f"Select recipe for {day}",
            [""] + recipe_names,
            index=(recipe_names.index(current) + 1) if current in recipe_names else 0,
            key=f"menu_{day}"
        )
        st.session_state.week_menu[day] = selected if selected else None

    st.divider()
    st.subheader("Your Weekly Menu")
    for day in days:
        recipe = st.session_state.week_menu[day]
        st.write(f"**{day}:** {recipe if recipe else 'No recipe selected'}")

    # Optionally: Save or export the menu
    if st.button("Save Weekly Menu"):
        st.success("Weekly menu saved in session!")