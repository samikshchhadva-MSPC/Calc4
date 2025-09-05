    # Placeholder monthly calculation loop
    years = list(range(1, policy_term + 1))
    data_bi, data_charges = [], []
    fund_4, fund_8 = 0, 0

    for yr in years:
        prem = annual_premium if yr <= ppt else 0

        # Premium Allocation Charges (PAC)
        pac = 0
        if yr == 1:
            pac = 0.06 * prem
        elif yr <= 5:
            pac = 0.04 * prem

        # Policy Admin Charges
        policy_admin = 0.0165 * prem if yr <= 5 else 0

        # Mortality charges (0.3% of risk cover)
        mort_chg_4 = 0.003 * max(sum_assured - fund_4, 0)
        mort_chg_8 = 0.003 * max(sum_assured - fund_8, 0)

        # GST (18% on charges excluding FMC)
        gst_4 = 0.18 * (mort_chg_4 + pac + policy_admin)
        gst_8 = 0.18 * (mort_chg_8 + pac + policy_admin)

        # Net investable before FMC
        invest_4 = prem - (pac + policy_admin + mort_chg_4 + gst_4)
        invest_8 = prem - (pac + policy_admin + mort_chg_8 + gst_8)

        # --- Monthly growth with FMC deduction ---
        monthly_rate_4 = (1 + 0.04) ** (1/12) - 1
        monthly_rate_8 = (1 + 0.08) ** (1/12) - 1
        monthly_fmc = 0.0135 / 12  # 1.35% annually

        for m in range(12):
            fund_4 = (fund_4 + (invest_4 / 12)) * (1 + monthly_rate_4) * (1 - monthly_fmc)
            fund_8 = (fund_8 + (invest_8 / 12)) * (1 + monthly_rate_8) * (1 - monthly_fmc)

        # Additions (placeholders for now)
        guaranteed_add = 0
        loyalty_add = 0
        booster_add = 0
        if yr >= 6:
            guaranteed_add = 0.0025 * fund_4
            loyalty_add = 0.0015 * fund_4 if ppt > 5 else 0
        if yr % 5 == 0 and yr >= 10:
            booster_add = 0.0275 * fund_4

        fund_4 += guaranteed_add + loyalty_add + booster_add
        fund_8 += guaranteed_add + loyalty_add + booster_add

        # Benefits
        surrender_4 = fund_4
        surrender_8 = fund_8
        death_ben_4 = max(surrender_4, sum_assured)
        death_ben_8 = max(surrender_8, sum_assured)

        # Table 1: Charges & Additions (now includes FMC)
        data_charges.append([
            yr, prem, pac, prem - pac, mort_chg_4, gst_4, policy_admin,
            round(monthly_fmc * 12 * 100, 2),  # FMC as % approx for display
            guaranteed_add, loyalty_add, booster_add
        ])

        # Table 2: BI
        data_bi.append([
            yr, prem,
            mort_chg_4, pac + policy_admin, gst_4, round(fund_4, 2), round(surrender_4, 2), round(death_ben_4, 2),
            mort_chg_8, pac + policy_admin, gst_8, round(fund_8, 2), round(surrender_8, 2), round(death_ben_8, 2)
        ])

    # Charges & Additions Table (extra FMC col)
    df_charges = pd.DataFrame(data_charges, columns=[
        "Policy Year", "Annualized Premium (AP)", "Premium Allocation Charge (PAC)",
        "Annualized Premium - PAC", "Mortality Charge", "GST",
        "Policy Admin. Charge", "Fund Mgmt. Charge (FMC)", 
        "Guaranteed Addition", "Loyalty Addition", "Booster Addition"
    ])
