import pandas as pd
import folium
import os

def create_map():
    # Load datasets
    pop_df = pd.read_csv('data/clean/BAY_school_population.csv')
    schools_df = pd.read_csv('data/clean/BAY_schools.csv')

    # Normalize LGA and State names for joining
    pop_df['LGA_norm'] = pop_df['LGA'].str.strip().str.lower()
    pop_df['State_norm'] = pop_df['State'].str.strip().str.lower()
    
    schools_df['lga_norm'] = schools_df['lga_name'].str.strip().str.lower()
    schools_df['state_norm'] = schools_df['state_name'].str.strip().str.lower()

    # Aggregate school data by LGA
    # We take the mean of lat/long to get a central point for the LGA markers
    lga_schools = schools_df.groupby(['state_norm', 'lga_norm']).agg({
        'id': 'count',
        'latitude': 'mean',
        'longitude': 'mean'
    }).reset_index()
    
    lga_schools.rename(columns={'id': 'school_count'}, inplace=True)

    # Merge population and school data
    merged = pd.merge(
        pop_df, 
        lga_schools, 
        left_on=['State_norm', 'LGA_norm'], 
        right_on=['state_norm', 'lga_norm'], 
        how='left'
    )

    # Fill missing school counts with 0 and use a default location if needed (though BAY schools should cover most)
    merged['school_count'] = merged['school_count'].fillna(0)
    
    # Calculate ratio: Children per School
    merged['children_per_school'] = merged['Estimated_School_Age_Pop_5_17'] / merged['school_count']
    merged.loc[merged['school_count'] == 0, 'children_per_school'] = merged['Estimated_School_Age_Pop_5_17']

    # Create map centered on the BAY region
    map_center = [merged['latitude'].mean(), merged['longitude'].mean()]
    m = folium.Map(location=map_center, zoom_start=7, tiles='CartoDB positron')

    # Add LGA markers
    for _, row in merged.iterrows():
        if pd.isna(row['latitude']) or pd.isna(row['longitude']):
            continue
            
        # Tooltip and Popup content
        popup_text = f"""
        <b>LGA:</b> {row['LGA']}<br>
        <b>State:</b> {row['State']}<br>
        <b>Est. School Age Pop:</b> {row['Estimated_School_Age_Pop_5_17']:,}<br>
        <b>Available Schools:</b> {int(row['school_count'])}<br>
        <b>Children per School:</b> {row['children_per_school']:.1f}
        """
        
        # Scale radius by population (square root for visual area scaling)
        radius = (row['Estimated_School_Age_Pop_5_17'] ** 0.5) / 15
        
        # Color by ratio (higher ratio = more underserved)
        if row['children_per_school'] > 1000:
            color = 'red'
        elif row['children_per_school'] > 500:
            color = 'orange'
        else:
            color = 'green'

        folium.CircleMarker(
            location=[row['latitude'], row['longitude']],
            radius=radius,
            popup=folium.Popup(popup_text, max_width=300),
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.6,
            weight=1,
            tooltip=row['LGA']
        ).add_to(m)

    # Add a legend (as a floating HTML element)
    legend_html = '''
     <div style="position: fixed; 
     bottom: 50px; left: 50px; width: 200px; height: 130px; 
     border:2px solid grey; z-index:9999; font-size:14px;
     background-color: white; opacity: 0.8; padding: 10px;">
     <b>Children per School</b><br>
     <i class="fa fa-circle" style="color:red"></i> > 1000 (Underserved)<br>
     <i class="fa fa-circle" style="color:orange"></i> 500 - 1000<br>
     <i class="fa fa-circle" style="color:green"></i> < 500 (Better coverage)<br>
     <br>
     <i>Circle size represents total school-age population.</i>
     </div>
     '''
    m.get_root().html.add_child(folium.Element(legend_html))

    # Save the map
    os.makedirs('maps', exist_ok=True)
    m.save('maps/bay_schools_map.html')
    print("Map saved to maps/bay_schools_map.html")

if __name__ == "__main__":
    create_map()
