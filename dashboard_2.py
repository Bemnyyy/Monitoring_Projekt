import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime, timedelta
import glob
from config import EXPORT_DIR


@st.cache_data
def load_data(date_str):
    fahrten_file = os.path.join(EXPORT_DIR, f"Monitoring_fahrten_{date_str}.csv")
    halte_file = os.path.join(EXPORT_DIR, f"Monitoring_halte_{date_str}.csv")

    if not os.path.exists(fahrten_file) or not os.path.exists(halte_file):
        return None, None

    df_fahrten = pd.read_csv(fahrten_file, sep=";", decimal=",")
    df_halte = pd.read_csv(halte_file, sep=";", decimal=",")

    if 'verspeatung_minuten' in df_halte.columns:
        df_halte = df_halte.rename(columns={'verspeatung_minuten': 'verspaetung_minuten'})

    return df_fahrten, df_halte

def get_latest_csv_file():
    search_pattern = os.path.join(EXPORT_DIR, "Monitoring_fahrten_*.csv")
    files = glob.glob(search_pattern)
    if not files:
        return None
    files.sort()
    return files[-1]

st.sidebar.header("Filter")
selected_date = st.sidebar.date_input("Analysedatum", datetime.now().date() - timedelta(days=1))
date_str = selected_date.strftime("%Y-%m-%d")
df_fahrten, df_halte = load_data(date_str)
loaded_file_name = f"Monitoring_fahrten_{date_str}.csv"

if df_fahrten is None or df_halte is None:
    st.sidebar.warning(f"Keine Daten für den {selected_date.strftime('%d.%m.%Y')} vorhanden.")
    latest_file_path = get_latest_csv_file()
    
    if latest_file_path:
        filename = os.path.basename(latest_file_path)
        latest_date_str = filename.replace("Monitoring_fahrten_", "").replace(".csv", "")
        
        df_fahrten, df_halte = load_data(latest_date_str)
        loaded_file_name = filename
        st.sidebar.info(f"Ersatzweise geladen: Stand vom {latest_date_str}")
    else:
        st.error("Es wurden überhaupt keine Analysedaten im Export-Ordner gefunden. Bitte starte zuerst den Scraper/Analyzer.")
        st.stop()

st.title("ÖPNV Monitoring Dashboard - Bodensee Oberschwaben")
st.info(f"Geladene Datei: {loaded_file_name}")
route_type_mapping = {0: 'Tram', 1: 'U-Bahn', 2: 'Zug', 3: 'Bus', 4: 'Fähre'}
df_fahrten['route_type_desc'] = df_fahrten['route_type'].map(route_type_mapping).fillna('Unbekannt')

selected_route_types = st.sidebar.multiselect(
    'Verkehrsmittel auswählen',
    options=df_fahrten['route_type_desc'].unique(),
    default=df_fahrten['route_type_desc'].unique()
)
df_fahrten_filtered_type = df_fahrten[df_fahrten['route_type_desc'].isin(selected_route_types)]
selected_routes = st.sidebar.multiselect(
    'Linien auswählen',
    options=sorted(df_fahrten_filtered_type['route_short_name'].dropna().unique()),
    default=sorted(df_fahrten_filtered_type['route_short_name'].dropna().unique())
)
df_fahrten_filtered = df_fahrten_filtered_type[df_fahrten_filtered_type['route_short_name'].isin(selected_routes)]
tab1, tab2, tab3 = st.tabs(["KPI Übersicht", "Linien-Analyse", "Fahrten- & Haltestellendetails"])

with tab1:
    st.header("Key Performance Indicators (KPIs)")
    
    if not df_fahrten_filtered.empty:
        total_trips = len(df_fahrten_filtered)
        cancelled_trips = df_fahrten_filtered['fahrtausfall'].sum()
        additional_trips = df_fahrten_filtered['zusatzfahrt'].sum()
        reliability = ((total_trips - cancelled_trips) / total_trips) * 100 if total_trips > 0 else 100
        regular_trips = df_fahrten_filtered[~df_fahrten_filtered['fahrtausfall']]
        punctual_trips = len(regular_trips[regular_trips['abweichungen_minuten'] <= 5])
        punctuality = (punctual_trips / len(regular_trips)) * 100 if len(regular_trips) > 0 else 100
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Fahrten Gesamt", f"{total_trips}")
        col2.metric("Zuverlässigkeit", f"{reliability:.1f}%", help="Prozentualer Anteil der nicht ausgefallenen Fahrten")
        col3.metric("Pünktlichkeit (≤ 5 Min)", f"{punctuality:.1f}%")
        col4.metric("Ausfälle / Zusatzfahrten", f"{cancelled_trips} / {additional_trips}")
        st.subheader("Betriebsleistung (Kilometer)")
        col1, col2, col3 = st.columns(3)
        col1.metric("Soll-Wagenkilometer (vkm)", f"{df_fahrten_filtered['static_vkm'].sum():,.1f} km")
        col2.metric("Ist-Wagenkilometer (vkm)", f"{df_fahrten_filtered['ist_vkm'].sum():,.1f} km")
        col3.metric("Erbrachte Leistung", f"{(df_fahrten_filtered['ist_vkm'].sum() / df_fahrten_filtered['static_vkm'].sum() * 100):.1f}%" if df_fahrten_filtered['static_vkm'].sum() > 0 else "100%")
    else:
        st.info("Keine Daten für die ausgewählten Filterkriterien vorhanden.")

with tab2:
    st.header("Linienbezogene Verspätungsanalyse")
    
    if not df_fahrten_filtered.empty:
        df_linien_agg = df_fahrten_filtered.groupby('route_short_name', as_index=False)['abweichungen_minuten'].mean()
        df_linien_agg['route_short_name'] = df_linien_agg['route_short_name'].astype(str)
        df_linien_agg = df_linien_agg.sort_values(by='abweichungen_minuten', ascending=False)
        st.subheader("Top Linien mit den größten Abweichungen")
        max_lines = st.slider("Anzahl der angezeigten Linien", min_value=5, max_value=50, value=15)
        df_plot = df_linien_agg.head(max_lines)
        fig_linien = px.bar(
            df_plot, 
            x='route_short_name', 
            y='abweichungen_minuten',
            title=f"Top {max_lines} Linien nach durchschnittlicher Abweichung",
            labels={'route_short_name': 'Liniennummer', 'abweichungen_minuten': 'Ø Abweichung (Minuten)'},
            color='abweichungen_minuten',
            color_continuous_scale='Reds'
        )
        fig_linien.update_layout(xaxis_type='category')
        
        st.plotly_chart(fig_linien, width="stretch")
    else:
        st.info("Keine Daten für die Grafik vorhanden.")

with tab3:
    st.header("Detailierte Fahrten-Tabelle")
    
    if not df_fahrten_filtered.empty:
        display_cols = {
            'trip_id': 'Fahrt-ID',
            'route_short_name': 'Linie',
            'route_type_desc': 'Verkehrsmittel',
            'start_time': 'Soll-Abfahrt',
            'abweichungen_minuten': 'Abweichung (Min)',
            'fahrtausfall': 'Ausfall',
            'zusatzfahrt': 'Zusatzfahrt'
        }
        
        available_cols = [col for col in display_cols.keys() if col in df_fahrten_filtered.columns]
        df_display = df_fahrten_filtered[available_cols].rename(columns=display_cols)

        st.dataframe(df_display, width="stretch", hide_index=True)
        
        st.subheader("Haltestellen-Verlauf für einzelne Fahrt prüfen")
        selected_trip = st.selectbox("Fahrt-ID für Haltestellen-Details auswählen", options=df_fahrten_filtered['trip_id'].unique())
        
        if selected_trip:
            df_halte_trip = df_halte[df_halte['trip_id'] == str(selected_trip)].sort_values(by='stop_sequence')
            if not df_halte_trip.empty:

                halte_cols = {
                    'stop_sequence': 'Nr.',
                    'stop_name': 'Haltestelle',
                    'departure_time': 'Geplante Zeit',
                    'arrival_time': 'Ankunftszeit',
                    'verspaetung_minuten': 'Verspätung (Min)',
                    'haltausfall': 'Halt ausgefallen',
                    'zusatzhalt': 'Zusätzlicher Halt'
                }

                available_halte_cols = [col for col in halte_cols.keys() if col in df_halte_trip.columns]
                df_halte_display = df_halte_trip[available_halte_cols].rename(columns=halte_cols)

                st.dataframe(df_halte_display, width="stretch", hide_index=True)
            else:
                st.info("Keine Haltestellendaten für diese Fahrt-ID gefunden.")
    else:
        st.info("Keine Detaildaten für die ausgewählten Filter vorhanden.")