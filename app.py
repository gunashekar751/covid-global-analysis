import os
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Global Covid 19 Analysis", layout="wide")

@st.cache_data
def load(stamp):
    trend = pd.read_csv("data/covid_trend.csv", parse_dates=["date"])
    summ = pd.read_csv("data/country_summary.csv")
    return trend, summ

trend, summ = load(os.path.getmtime("data/covid_trend.csv") + os.path.getmtime("data/country_summary.csv"))

st.markdown("<style>.block-container{padding-top:2.5rem}</style>", unsafe_allow_html=True)
st.markdown("<div style='text-align:center;font-size:3.2rem;font-weight:800;letter-spacing:.08em;color:#ff4b4b;line-height:1.1'>COVID-19 DATA DASHBOARD</div>", unsafe_allow_html=True)
st.markdown("<div style='text-align:center;font-size:1.5rem;font-weight:600;margin-top:.4rem'>Global Covid 19 Analysis</div>", unsafe_allow_html=True)
st.markdown(f"<div style='text-align:center;font-size:1.05rem;color:#9aa4b2;margin-bottom:.6rem'>{trend['country'].nunique()} countries &nbsp;|&nbsp; March 2020 to June 2023</div>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center;color:#9aa4b2'>Official COVID-19 figures from Our World in Data, March 2020 to June 2023. Counts depend on how each country reported deaths, so compare with care.</p>", unsafe_allow_html=True)

# Sidebar controls
countries = sorted(trend["country"].unique())
focus = ["Brazil", "Germany", "India", "Japan", "South Africa", "Sweden", "United Kingdom", "United States"]
st.sidebar.markdown("<div style='font-size:1.3rem;font-weight:700;color:#ff4b4b'>Country selection</div>", unsafe_allow_html=True)
st.sidebar.caption("Choose which countries appear in every chart.")
mode = st.sidebar.radio("Start with", ["All countries", "8 focus countries"])
default = countries if mode == "All countries" else [c for c in focus if c in countries]
sel = st.sidebar.multiselect("Countries", countries, default=default, key="sel_" + mode)
st.sidebar.caption(f"{len(sel)} of {len(countries)} countries selected")
metrics = {"Deaths per million (7-day avg)": "new_deaths_smoothed_per_million", "Cases per million (7-day avg)": "new_cases_smoothed_per_million", "Fully vaccinated per 100": "people_fully_vaccinated_per_hundred", "Stringency index": "stringency_index"}
st.sidebar.markdown("<div style='font-size:1.3rem;font-weight:700;color:#ff4b4b;margin-top:1rem'>Chart settings</div>", unsafe_allow_html=True)
label = st.sidebar.selectbox("Metric", list(metrics))
col = metrics[label]
d0, d1 = trend["date"].min().date(), trend["date"].max().date()
start, end = st.sidebar.slider("Date range", d0, d1, (d0, d1))

df = trend[trend["country"].isin(sel) & trend["date"].between(pd.Timestamp(start), pd.Timestamp(end))]
if df.empty:
    st.warning("No data for this selection.")
    st.stop()

# KPI tiles
k1, k2, k3 = st.columns(3)
deaths = df["new_deaths_smoothed_per_million"]
if deaths.notna().any():
    peak = df.loc[deaths.idxmax()]
    k1.metric("Peak daily deaths per million", f"{peak['new_deaths_smoothed_per_million']:.1f}")
    k1.caption(f"{peak['country']}, {peak['date']:%b %Y}")
k2.metric("Avg total deaths per million (selected)", f"{df.groupby('country')['total_deaths_per_million'].last().mean():,.0f}")
k3.metric("Highest fully vaccinated (per 100)", f"{df['people_fully_vaccinated_per_hundred'].max():.0f}")

tab1, tab2, tab3 = st.tabs(["Trends", "World map", "Worldwide impact"])

with tab1:
    view = st.radio("View", ["Small panels", "Heatmap", "Ranking"], horizontal=True, index=1 if mode == "All countries" else 0)
    if view == "Small panels":
        dfp = df
        if df["country"].nunique() > 16:
            top = df.groupby("country")[col].max().nlargest(16).index
            dfp = df[df["country"].isin(top)]
            st.info("Small panels show the 16 countries with the highest values. Use Heatmap or Ranking to see every selected country, or narrow your selection.")
        else:
            st.caption("Each panel uses the same vertical scale, so countries can be compared fairly.")
        n = dfp["country"].nunique()
        fig = px.area(dfp, x="date", y=col, color="country", facet_col="country", facet_col_wrap=4, height=max(520, 190 * ((n + 3) // 4)), labels={col: label})
        fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
        fig.update_traces(connectgaps=True)
        fig.update_xaxes(title=None, tickformat="%Y", dtick="M12")
        fig.update_layout(showlegend=False)
    elif view == "Heatmap":
        st.caption("Monthly average per country, highest first. Darker means higher. Blank means no data.")
        m = df.assign(month=df["date"].dt.to_period("M").dt.to_timestamp()).groupby(["country", "month"])[col].mean().reset_index()
        pivot = m.pivot(index="country", columns="month", values=col)
        pivot = pivot.loc[pivot.max(axis=1).sort_values(ascending=False).index]
        fig = px.imshow(pivot, aspect="auto", color_continuous_scale="Reds", labels=dict(x="Month", y="Country", color=label))
        fig.update_yaxes(dtick=1)
        fig.update_layout(height=max(400, 16 * len(pivot)))
    else:
        st.caption("Highest value reached by each country in the selected period.")
        rank = df.groupby("country")[col].max().sort_values().reset_index()
        fig = px.bar(rank, x=col, y="country", orientation="h", labels={col: "Highest value of " + label})
        fig.update_layout(height=max(400, 18 * len(rank)))
    st.plotly_chart(fig)

with tab2:
    s2 = summ[summ["country"].isin(sel)]
    st.caption(f"Showing the {len(s2)} selected countries. Pick fewer in the sidebar to focus the map.")
    fig = px.choropleth(s2, locations="code", color="deaths_pm", hover_name="country", color_continuous_scale="Reds", range_color=(0, summ["deaths_pm"].max()), labels={"deaths_pm": "Deaths per million"})
    fig.update_geos(projection_type="natural earth", showframe=False, bgcolor="rgba(0,0,0,0)", showocean=True, oceancolor="#0b1226", landcolor="#1b2440", countrycolor="#3a4766")
    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0))
    st.plotly_chart(fig)

with tab3:
    by = st.radio("Slice by", ["Continent", "Country (top 10)"], horizontal=True)
    tot = df.groupby("country").agg(continent=("continent", "first"), pop=("population", "first"), dpm=("total_deaths_per_million", "last")).dropna()
    tot["deaths"] = tot["dpm"] * tot["pop"] / 1e6
    if by == "Continent":
        pie = tot.groupby("continent")["deaths"].sum().reset_index()
        names = "continent"
    else:
        top = tot["deaths"].nlargest(10)
        pie = top.reset_index()
        other = tot["deaths"].sum() - top.sum()
        if other > 0:
            pie = pd.concat([pie, pd.DataFrame({"country": ["All other countries"], "deaths": [other]})])
        names = "country"
    st.caption(f"Where reported COVID-19 deaths were recorded across the {len(tot)} selected countries, up to the end of your date range. Reported counts, so countries that undercounted look smaller than they were.")
    fig = px.pie(pie, names=names, values="deaths", hole=0.45, color_discrete_sequence=px.colors.qualitative.Set2)
    fig.update_traces(textinfo="percent", hovertemplate="%{label}: %{value:,.0f} deaths (%{percent})")
    fig.update_layout(height=520, annotations=[dict(text=f"{tot['deaths'].sum() / 1e6:.2f}M<br>deaths", showarrow=False, font_size=20)])
    st.plotly_chart(fig)