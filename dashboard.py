import streamlit as st
import pandas as pd
import plotly.express as px
import glob
import os
from config import EXPORT_DIR

# site configuration
st.set_page_config(page_title="Bodensee Oberschwaben Verkehrsverbund ÖPNV Monitor", layout="wide")

def get_latest_csv_file():
    #creating search mask
    search_pattern = os.path.join(EXPORT_DIR, "Monitoring_fahrten_*.csv")
    files = glob.glob(search_pattern) # lists all csv file
    if not files:
        return None
    files.sort()
    return files[-1]

# loading data
@st.cache_data
def load_data():
    latest_file_path = get_latest_csv_file()
    if latest_file_path is None:
        st.error(f"Fehler: Keine Monitoring-Fahrten-CSV im hinterlegten Ordner '{EXPORT_DIR}' gefunden.")
        st.info("Stellen Sie sicher, dass der Pfad in der `.end` korrekt ist.")
        st.stop()

    df = pd.read_csv(latest_file_path, sep=';', decimal=',', encoding='utf-8-sig')
    file_name = os.path.basename(latest_file_path)
    return df, file_name

# getting DataFrame and name of loaded file
df, loaded_file_name = load_data()
st.title("ÖPNV Monitoring Dashboad - Bodensee Oberschwaben")

try:
    current_date = loaded_file_name.split("_")[-1].replace(".csv", "")
    st.info(f"**Aktueller Datenstand vom Betriebstag:** {current_date} *(Geladene Datei: {loaded_file_name})*")
except:
    st.info(f"Geladene Datei: {loaded_file_name}")

st.markdown("Interaktive Auswertung der Fahrten- und Pünktlichkeitsdaten basierend auf GTFS und GTFS-Realtime.")
# adding filter to sidebar
st.sidebar.header("Filter")
only_active = st.sidebar.checkbox("Nur Linien mit Live-Daten anzeigen", value=True, help="Blendet Linien aus, für die im aktuellen Snapshot keine Echtzeitdaten vorliegen.")
if only_active:
    active_routes = df[df["RT_vorhanden"] == True]["route_long_name"].unique()
    display_df = df[df["route_long_name"].isin(active_routes)]
else:
    display_df = df

route_list = ["Alle Linien"] + list(display_df['route_long_name'].dropna().unique())
selected_route = st.sidebar.selectbox("Wähle eine Linie:", route_list)
#filter data based of what was picked
if selected_route != "Alle Linien":
    filtered_df = display_df[display_df["route_long_name"] == selected_route]
else:
    filtered_df = display_df

# calculate KPI-Metric
total_trips = len(filtered_df)
rt_true = filtered_df["RT_vorhanden"].sum()
ausfaelle = filtered_df["fahrtausfall"].sum()
zusatz = filtered_df["zusatzfahrt"].sum()
avg_delay = filtered_df[filtered_df["RT_vorhanden"] == True]["abweichungen_minuten"].mean()

if pd.isna(avg_delay):
    avg_delay = 0

# show KPI-maps
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric(label="Fahrten (Soll)", value=total_trips)
with col2:
    st.metric(label="Erfasste Live-Fahrten", value=rt_true)
with col3:
    st.metric(label="Fahrtausfälle", value=ausfaelle, delta=f"{(ausfaelle/total_trips*100):.1f}%" if total_trips>0 else "0%")
with col4:
    st.metric(label="Ø Verspätung (Min)", value=f"{avg_delay:.2f}")

st.markdown("---")

#show diagramms
chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    st.subheader("Fahrt-Status Übersicht")
    pünktlich_oder_verspätet = rt_true - zusatz
    status_counts = pd.DataFrame({
        'Status': ['Regulär (Live)', 'Ausfall', 'Zusatzfahrt'],
        'Anzahl': [pünktlich_oder_verspätet, ausfaelle, zusatz]
    })
    fig_pie = px.pie(status_counts, values='Anzahl', names='Status', hole=0.4, 
                     color='Status', color_discrete_map={'Regulär (Live)':'#2ecc71', 'Ausfall':'#e74c3c', 'Zusatzfahrt':'#3498db'})
    st.plotly_chart(fig_pie, width="stretch")

with chart_col2:
    st.subheader("Verteilung der Verspätungen")
    delay_data = filtered_df[(filtered_df['RT_vorhanden'] == True) & (~filtered_df['fahrtausfall'])]
    if not delay_data.empty:
        fig_hist = px.histogram(delay_data, x="abweichungen_minuten", nbins=20,
                                labels={'abweichungen_minuten':'Verspätung in Minuten'},
                                color_discrete_sequence=['#f39c12'])
        st.plotly_chart(fig_hist, width="stretch")
    else:
        st.info("Keine Verspätungsdaten für diese Auswahl vorhanden.")

st.markdown("---")

st.subheader("Top 10 Linien mit der höchsten Ø Verspätung")
delay_routes = filtered_df[filtered_df['RT_vorhanden'] == True]

if not delay_routes.empty:
    top_delayed = delay_routes.groupby('route_long_name')['abweichungen_minuten'].mean().reset_index()
    top_delayed = top_delayed.sort_values(by='abweichungen_minuten', ascending=True).tail(10)
    
    fig_top_delay = px.bar(
        top_delayed, 
        x='abweichungen_minuten', 
        y='route_long_name', 
        orientation='h',
        labels={'abweichungen_minuten': 'Ø Verspätung (Minuten)', 'route_long_name': 'Linie'},
        color='abweichungen_minuten',
        color_continuous_scale=px.colors.sequential.Reds
    )
    st.plotly_chart(fig_top_delay, width="stretch")
else:
    st.info("Keine Echtzeitdaten für eine Verspätungsanalyse vorhanden.")

st.markdown("---")

st.subheader("Erbrachte Betriebsleistung (Soll vs. Ist VKM)")
vkm_performance = filtered_df.groupby('route_long_name')[['static_vkm', 'ist_vkm']].sum().reset_index()

if not vkm_performance.empty:
    vkm_performance = vkm_performance.sort_values(by='static_vkm', ascending=False).head(15)
    vkm_melted = vkm_performance.melt(id_vars='route_long_name', value_vars=['static_vkm', 'ist_vkm'], var_name='Leistungsart', value_name='Kilometer')
    vkm_melted['Leistungsart'] = vkm_melted['Leistungsart'].map({'static_vkm': 'Geplante VKM (Soll)', 'ist_vkm': 'Gefahrene VKM (Ist)'})

    fig_vkm = px.bar(
        vkm_melted,
        x='route_long_name',
        y='Kilometer',
        color='Leistungsart',
        barmode='group',
        labels={'Kilometer': 'Fahrzeugkilometer (VKM)', 'route_long_name': 'Linie'},
        color_discrete_map={'Geplante VKM (Soll)': '#95a5a6', 'Gefahrene VKM (Ist)': "#2cec45"}
    )
    fig_vkm.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig_vkm, width="stretch")
else:
    st.info("Keine VKM-Leistungsdaten vorhanden.")

# show data table
with st.expander("Rohdaten ansehen"):
    st.dataframe(filtered_df[['trip_id', 'route_long_name', 'soll_fahrplanminuten', 'ist_fahrplanminuten', 'abweichungen_minuten']])