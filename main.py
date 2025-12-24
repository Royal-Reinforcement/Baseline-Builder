import streamlit as st
import smartsheet
import pandas as pd

APP_NAME = 'Baseline Builder'

st.set_page_config(page_title=APP_NAME, page_icon='🏗️', layout='centered')

st.image(st.secrets['images']["rr_logo"], width=100)

st.title(APP_NAME)
st.info('Build a new baseline for a unit using the Escapia Nightly Rates Export.')

@st.cache_data(ttl=300)
def smartsheet_to_dataframe(sheet_id):
    smartsheet_client = smartsheet.Smartsheet(st.secrets['smartsheet']['access_token'])
    sheet             = smartsheet_client.Sheets.get_sheet(sheet_id)
    columns           = [col.title for col in sheet.columns]
    rows              = []
    for row in sheet.rows: rows.append([cell.value for cell in row.cells])
    return pd.DataFrame(rows, columns=columns)





sdf     = smartsheet_to_dataframe(st.secrets['smartsheet']['sheets']['seasons'])
file    = st.file_uploader('**Nightly Rates Export** | Escapia > Rates > Rates Manager > Export your rates', type='csv')

if file:

    sdf['Start_Date']   = pd.to_datetime(sdf['Start_Date'])
    sdf['End_Date']     = pd.to_datetime(sdf['End_Date'])

    df                  = pd.read_csv(file)
    df                  = df.drop(columns=['Unit Name'])
    df                  = df.sort_values(by='Unit Code')
    df                  = df.melt(id_vars=['Unit Code'], var_name='Date', value_name='Daily_Rate')
    df['Date']          = pd.to_datetime(df['Date'])
    df['Daily_Rate']    = df['Daily_Rate'].astype(float)

    l, r                = st.columns(2)
    unit                = l.selectbox('Unit', df['Unit Code'].unique(), index=None)
    discount            = r.slider('Percentage from Baseline', min_value=-100, max_value=100, value=0, step=1)

    if unit is not None:

        df = df[df['Unit Code'] == unit]
        df['Daily_Rate'] = df['Daily_Rate'] * (1 + discount / 100)
        
        def get_season(row):
            for _, season in sdf.iterrows():
                if season['Start_Date'] <= row['Date'] <= season['End_Date']:
                    return season['Season']
            return 'Other'
        
        df['Season']                = df.apply(get_season, axis=1)

        grouped_df                  = df.groupby('Season').agg({'Daily_Rate': ['mean', 'count']}).reset_index()
        grouped_df.columns          = ['Season', 'Daily_Rate', 'Nights']
        grouped_df['Weekly_Rate']   = grouped_df['Daily_Rate'] * 7
        grouped_df                  = grouped_df[['Season', 'Daily_Rate', 'Weekly_Rate']]
        grouped_df                  = grouped_df[grouped_df['Season'] != 'Other']
        grouped_df                  = grouped_df.sort_values(by='Season', key=lambda x: [sdf[sdf['Season'] == s].index[0] for s in x])
        grouped_df                  = grouped_df.set_index('Season')

        final                       = pd.merge(sdf, grouped_df, on='Season')
        final['Start_Date']         = final['Start_Date'].dt.strftime('%Y-%m-%d')
        final['End_Date']           = final['End_Date'].dt.strftime('%Y-%m-%d')
        final['Daily_Rate']         = final['Daily_Rate'].round(2)
        final['Weekly_Rate']        = final['Weekly_Rate'].round(2)

        filename                    = f'{str(unit).strip().replace(r"[\t\n\r]", "")}_{discount}_{pd.to_datetime(pd.Timestamp.now()).strftime("%Y-%m-%d")}.csv'
        
        st.dataframe(final, width='stretch', hide_index=True)
        st.download_button('DOWNLOAD', final.to_csv(index=False), file_name=filename, mime='text/csv', type='primary', width='stretch')

        l, r = st.columns(2)
        l.metric('Minimum Rate', round(final['Daily_Rate'].min(), 2))
        r.metric('Season with Minimum Rate', final.loc[final['Daily_Rate'].idxmin(), 'Season'])