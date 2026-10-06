import openpyxl
from openpyxl.utils import get_column_letter
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
P="/mnt/user-data/outputs/Henkel_MA_Financing_Model_teilverkauf_ccy.xlsx"
wb=openpyxl.load_workbook(P)
FONT="Arial"
def F(sz=10,b=False,color="000000",it=False): return Font(name=FONT,size=sz,bold=b,color=color,italic=it)
YELLOW=PatternFill("solid",fgColor="FFF2CC"); HEADERBG=PatternFill("solid",fgColor="1F3864"); BANDBG=PatternFill("solid",fgColor="EEF3FA")
thin=Side(style="thin",color="BFBFBF"); BORDER=Border(left=thin,right=thin,top=thin,bottom=thin)
BLUE="0000FF"; GREEN="008000"; GREY="555555"; WHITE="FFFFFF"
NUM_MM='#,##0.0;(#,##0.0);"-"'; PCT1='0.0%'; EPS4='0.0000'
def put(ws,a,v,font=None,fillc=None,num=None,align=None,wrap=False,border=False):
    c=ws[a]; c.value=v; c.font=font or F()
    if fillc: c.fill=fillc
    if num: c.number_format=num
    if align or wrap: c.alignment=Alignment(horizontal=align,vertical="center",wrap_text=wrap)
    if border: c.border=BORDER
    return c
NY=8
E3="'E3 · Cost & Schedule'"; E4="'E4 · KPIs & Funding'"; DI="'1. Deal Inputs'"; TP="'2. Target Plan'"; MIX="'3. Scenario & Mix'"
DA=f"{TP}!$B$11"; BLEND=f"{TP}!$B$10"; OPTAX=f"{DI}!$B$42"; SHIELD=f"{E4}!$B$96"; SHARES=f"{DI}!$B$44"

mix=wb["3. Scenario & Mix"]; hs=wb["Henkel Summary"]

# ---------- Tab 3: per-currency EBITDA margin (col H) + resolved helper (col K, hidden) ----------
put(mix,"H7","EBITDA margin per ccy (optional — for EXACT partial-sale earnings; blank = plan margin)",F(8,True,WHITE),HEADERBG,align="center",wrap=True,border=True)
put(mix,"K7","resolved margin (helper)",F(7,False,GREY,it=True))
for r in range(8,30):
    if mix[f"A{r}"].value:   # a currency row
        put(mix,f"H{r}",None,F(9,True,BLUE),YELLOW,PCT1,align="center",border=True)
        put(mix,f"K{r}",f'=IF(ISNUMBER(H{r}),H{r},{BLEND})',F(7,False,GREY),None,PCT1)
mix.column_dimensions["K"].hidden=True
# reconciliation (NES-weighted EBITDA margin) — informational, at H31 is free? use a labelled cell at A31 area is merged; put at E7? use K30/K31 hidden + show on HS. Put a visible check at H30 is taken -> put at row 31 col K hidden, and a visible note cell:
put(mix,"H8",None)  # keep input
# ---------- Henkel Summary: rewire operating share helper N96..N101 to EBIT-share ----------
for k in range(6):
    rr=96+k
    # N = (G_sold*(K_sold-DA)) / (SUMPRODUCT(G,K) - DA*SUM(G))   -> EBIT share of the sold currency
    put(hs,f"N{rr}",
        f'=IFERROR((INDEX({MIX}!$G$8:$G$29,$M${rr})*(INDEX({MIX}!$K$8:$K$29,$M${rr})-{DA}))/(SUMPRODUCT({MIX}!$G$8:$G$29,{MIX}!$K$8:$K$29)-{DA}*SUM({MIX}!$G$8:$G$29)),0)',
        F(7,False,GREY))
# relabel row 79
put(hs,"A79","Operating-earnings retained factor (entity sales; EXACT EBIT share via per-ccy margins)",F(9))
# ---------- new rows 91-94: post-sale operating EBIT + post-sale EPS ----------
put(hs,"A91","► POST-SALE OPERATING & EPS — acquirer (uses the exact per-currency EBIT share, row 79)",F(11,True,WHITE),HEADERBG); hs.merge_cells("A91:J91")
put(hs,"A92","Post-sale operating EBIT — acquirer (EUR mm)",F(9))
put(hs,"A93","► Post-sale EPS — acquirer (€/share)",F(9,True))
for j in range(NY):
    cl=get_column_letter(3+j)
    put(hs,f"{cl}92",f'=IFERROR({E4}!{cl}$54*{cl}79,"")',F(9),None,NUM_MM,align="center")
    eps=(f'({E4}!{cl}$54*{cl}79*(1-{OPTAX})'                              # operating, retained, after group tax
         f'+({E3}!{cl}$70+{cl}75)*(1-{SHIELD})'                          # financing after shield (full net fin + shed interest you no longer pay)
         f'-{E3}!{cl}$208*IF({E3}!{cl}$65>0.0001,{cl}76/{E3}!{cl}$65,1))'# WHT scaled to remaining interest
         f'/{SHARES}')
    put(hs,f"{cl}93",f'=IF(NOT(ISNUMBER({SHARES})),"—",IFERROR({eps},""))',F(9,True,GREEN),None,EPS4,align="center")
put(hs,"A94",f'=IFERROR("Operating earnings use per-currency EBITDA margins (Tab 3 col H; blank = plan "&TEXT({BLEND},"0.0%")&"). NES-weighted margin = "&TEXT(SUMPRODUCT({MIX}!$G$8:$G$29,{MIX}!$K$8:$K$29)/SUM({MIX}!$G$8:$G$29),"0.0%")&". Financing after-tax; WHT scales with remaining interest.","Per-currency EBITDA margins on Tab 3 col H refine the operating side.")',F(8,False,GREY,it=True)); hs.merge_cells("A94:J94")

try: wb.calculation.fullCalcOnLoad=True; wb.calculation.calcId=0
except Exception as e: print("calc:",e)
wb.save(P)
print("SAVED — operative EPS refinement in:",P)
print("sheets:",len(wb.sheetnames))
