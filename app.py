import streamlit as st
from data_parser import load_match_data
from report_generator import generate_report

st.set_page_config(
    page_title="BKFC Match Report",
    page_icon="⚽",
    layout="wide"
)

# Application Theme Framework Title Elements
st.title("⚽ Brooklyn FC")
st.subheader("Match Analysis & Report Generator")
st.markdown("---")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### Primary Data Inputs")
    bkfc_file = st.file_uploader("Upload BKFC Wyscout Season Database (.xlsx)", type=["xlsx"])

with col2:
    st.markdown("### Opponent Data Inputs")
    opp_file = st.file_uploader("Upload Opponent Wyscout Season Database (.xlsx)", type=["xlsx"])

if bkfc_file and opp_file:
    try:
        # Load and execute transformation mapping engine pipeline
        data = load_match_data(bkfc_file, opp_file)
        
        st.success(f"Successfully Found Match Record: BKFC vs {data['opponent_name']}")
        
        # Display contextual parameters validation card
        with st.container():
            st.markdown("#### Match Validation")
            meta1, meta2, meta3 = st.columns(3)
            meta1.metric("Competition Stage", data['competition'])
            meta2.metric("Recorded Match Date", data['match_date'])
            meta3.metric("Final Scoreline", data['score'])
            
        st.markdown("---")
        confirm = st.checkbox("Verify data profiles match")

        if confirm:
            if st.button("Compile Match Report", use_container_width=True):
                with st.spinner("Processing visualizations..."):
                    # Process presentation array objects into bytes stream
                    report_stream = generate_report(data)
                    
                    # Create custom file name download output string matches
                    clean_opp_name = data['opponent_name'].replace(" ", "_")
                    output_filename = f"BKFC_vs_{clean_opp_name}_Match_Report.pptx"
                    
                st.balloons()
                st.download_button(
                    label="Download PowerPoint",
                    data=report_stream,
                    file_name=output_filename,
                    mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                    use_container_width=True
                )
    except Exception as e:
        st.error(f"Critical pipeline error encountered during execution loop processing: {str(e)}")
