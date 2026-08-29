## 2024-03-01 - Disabled states instead of conditional rendering
**Learning:** In Streamlit apps, hiding action buttons (like "Add to Queue", "Clear", "Download", "Remove") when there's no data or selection causes layout shifts and hurts discoverability.
**Action:** Always render the buttons but use `disabled=True` based on the data/selection state so users can see the available actions even if they can't perform them yet.
