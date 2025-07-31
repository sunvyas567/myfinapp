# config_data.py

ABOUT_APP_TEXT = """
### About the FUTURE FINANCE Simulator
Welcome to Your Financial Future Advisor.

Plan smarter, live better. Our app helps you visualize your Financial journey by forecasting your income, investments (FDs and other schemes), and expenses—adjusted for inflation—so you stay secure and stress-free in the years ahead.

**Note:** This is a simulation tool intended for planning and guidance purposes only. It does not provide real-time financial forecasting or professional financial advice.
"""

BASE_DATA_CONFIG = [
    {'Field Description': 'Age', 'Field Name': 'GLAge', 'Field Default Value': 58, 'Field Input': ''},
    {'Field Description': 'Gender', 'Field Name': 'GLGender', 'Field Default Value': 'Male', 'Field Input': ''},
    {'Field Description': 'Projection Years', 'Field Name': 'GLProjectionYears', 'Field Default Value': 1, 'Field Input': ''},
    {'Field Description': 'Inflation Rate', 'Field Name': 'GLInflationRate', 'Field Default Value': 10.0, 'Field Input': ''},
    {'Field Description': 'Sr Citizen FD Rate', 'Field Name': 'GLSrCitizenFDRate', 'Field Default Value': 7.4, 'Field Input': ''},
    {'Field Description': 'Normal FD rate', 'Field Name': 'GLNormalFDRate', 'Field Default Value': 6.5, 'Field Input': ''},
    {'Field Description': 'SWP Growth Rate', 'Field Name': 'GLSWPGrowthRate', 'Field Default Value': 10.0, 'Field Input': ''},
    {'Field Description': 'SWP monthly Rate', 'Field Name': 'GLSWPMonthlyRate', 'Field Default Value': '=(1 + {GLSWPGrowthRate}/100) ** (1 / 12) - 1', 'Field Input': '=(1 + {GLSWPGrowthRate}/100) ** (1 / 12) - 1'},
    {'Field Description': 'SWP monthly withdrawal', 'Field Name': 'GLSWPMonthlyWithdrawal', 'Field Default Value': 15000, 'Field Input': ''},
    {'Field Description': 'SWP LCTG Exemption', 'Field Name': 'GLSWPLCTGExemption', 'Field Default Value': 100000, 'Field Input': ''},
    {'Field Description': 'SWP LCTG tax slab', 'Field Name': 'GLSWPLCTGTaxSlab', 'Field Default Value': 20.0, 'Field Input': ''},
    {'Field Description': 'SSCS rate', 'Field Name': 'GLSCSSRate', 'Field Default Value': 8.2, 'Field Input': ''},
    {'Field Description': 'POMIS rate', 'Field Name': 'GLPOMISRate', 'Field Default Value': 7.5, 'Field Input': ''},
    {'Field Description': 'POMIS Allowed Amount Single', 'Field Name': 'GLPOMISSingle', 'Field Default Value': 900000, 'Field Input': ''},
    {'Field Description': 'POMIS Allowed Amount Joint', 'Field Name': 'GLPOMISJoint', 'Field Default Value': 1500000, 'Field Input': ''},
    {'Field Description': 'SCSS Allowed Amount Single', 'Field Name': 'GLSCSSSingle', 'Field Default Value': 3000000, 'Field Input': ''},
    {'Field Description': 'SCSS Allowed Amount Joint', 'Field Name': 'GLSCSSJoint', 'Field Default Value': 6000000, 'Field Input': ''},
    {'Field Description': 'Current Monthly Rental', 'Field Name': 'GLCurrentMonthlyRental', 'Field Default Value': 20000, 'Field Input': ''},
    {'Field Description': 'Max Monthly Rental', 'Field Name': 'GLMaxMonthlyRental', 'Field Default Value': 30000, 'Field Input': ''},
    {'Field Description': 'Annuity Existing - Monthly', 'Field Name': 'GLAnnuityExistingMonthly', 'Field Default Value': 1500, 'Field Input': ''},
    {'Field Description': 'Annuity New via PPF Superannuation, NPS funds', 'Field Name': 'GLAnnuityNew', 'Field Default Value': 0, 'Field Input': ''},
    {'Field Description': 'Pension From EPS Etc', 'Field Name': 'GLPensionEPS', 'Field Default Value': 2000, 'Field Input': ''},
    {'Field Description': 'Current Shares Dividend Income', 'Field Name': 'GLDividendIncome', 'Field Default Value': 200000, 'Field Input': ''},
    {'Field Description': 'PF Accumulation', 'Field Name': 'GLPFAccumulation', 'Field Default Value': 7500000, 'Field Input': ''},
    {'Field Description': 'PPF Accumulation', 'Field Name': 'GLPPFAccumulation', 'Field Default Value': 0, 'Field Input': ''},
    {'Field Description': 'Superannuation', 'Field Name': 'GLSuperannuation', 'Field Default Value': 0, 'Field Input': ''},
    {'Field Description': 'Agriculture income', 'Field Name': 'GLAgricultureIncome', 'Field Default Value': 0, 'Field Input': ''},
    {'Field Description': 'Trading Income - stocks', 'Field Name': 'GLTradingIncome', 'Field Default Value': 0, 'Field Input': ''},
    {'Field Description': 'Land-flat buy and sell', 'Field Name': 'GLRealStateIncome', 'Field Default Value': 0, 'Field Input': ''},
    {'Field Description': 'Consulting Income', 'Field Name': 'GLConsultingIncome', 'Field Default Value': 0, 'Field Input': ''},
    {'Field Description': 'SWP investment percentage from total corpus', 'Field Name': 'GLSWPInvestmentPercentage', 'Field Default Value': 30.0, 'Field Input': ''},
    {'Field Description': 'Non-SWP investment percentage from total corpus', 'Field Name': 'GLNonSWPInvestmentPercentage', 'Field Default Value': 70.0, 'Field Input': ''},
    {'Field Description': 'Normal FD investment % post POMIS & SCSS', 'Field Name': 'GLNormalFDExcludingPOMISSCSS', 'Field Default Value': 10.0, 'Field Input': ''},
    {'Field Description': 'Sr Citizen FD Investment % post POMIS & SCSS', 'Field Name': 'GLSrCitizenFDExcludingPOMISSCSS', 'Field Default Value': 90.0, 'Field Input': ''}
]

ONETIME_EXPENSES_CONFIG = [
    {'Field Description': 'Kids education', 'Field Name': 'LocalKidsEducation', 'Field Default Value': 700000, 'Field Input': '', 'Type': 'Must'},
    {'Field Description': 'House renovation', 'Field Name': 'LocalHouseRenovation', 'Field Default Value': 1500000, 'Field Input': '', 'Type': 'Must'},
    {'Field Description': 'Car and Other Vehicle renewal', 'Field Name': 'LocalVehicleRenewal', 'Field Default Value': 700000, 'Field Input': '', 'Type': 'Must'},
    {'Field Description': 'Jewelry Ornaments etc', 'Field Name': 'LocalJewelry', 'Field Default Value': 100000, 'Field Input': '', 'Type': 'Must'},
    {'Field Description': 'Travel - Outside', 'Field Name': 'LocalTravelForeign', 'Field Default Value': 1500000, 'Field Input': '', 'Type': 'Must'},
    {'Field Description': 'Others Expenses', 'Field Name': 'LocalOthers', 'Field Default Value': 0, 'Field Input': '', 'Type': 'Must'},
    {'Field Description': 'Total Initial One Time Planned Expenses - Must', 'Field Name': 'LocalTotalOneTimeMust', 'Field Default Value': '={LocalKidsEducation}+{LocalHouseRenovation}+{LocalVehicleRenewal}+{LocalJewelry}+{LocalTravelForeign}+{LocalOthers}', 'Field Input': '={LocalKidsEducation}+{LocalHouseRenovation}+{LocalVehicleRenewal}+{LocalJewelry}+{LocalTravelForeign}+{LocalOthers}', 'Type': 'Must'},
    {'Field Description': 'Marriages of children', 'Field Name': 'LocalMarriages', 'Field Default Value': 5000000, 'Field Input': '', 'Type': 'Delayed'},
    {'Field Description': 'Property Purchases - Land Flat Agriculture', 'Field Name': 'LocalProperty', 'Field Default Value': 3000000, 'Field Input': '', 'Type': 'Delayed'},
    {'Field Description': 'Total Initial One Time Planned Expenses - Delayed', 'Field Name': 'LocalTotalOneTimeDelayed', 'Field Default Value': '={LocalMarriages}+{LocalProperty}', 'Field Input': '={LocalMarriages}+{LocalProperty}', 'Type': 'Delayed'},
    {'Field Description': 'Total Initial One Time Planned Expenses', 'Field Name': 'GrandTotalOneTime', 'Field Default Value': '={LocalTotalOneTimeMust}+{LocalTotalOneTimeDelayed}', 'Field Input': '={LocalTotalOneTimeMust}+{LocalTotalOneTimeDelayed}', 'Type': 'Planned'}
]

RECURRING_EXPENSES_CONFIG = [
    {'Field Description': 'Grocery & vegetables (must)', 'Field Name': 'LocalGroceryVeg', 'Field Default Value': 35000, 'Field Input': ''},
    {'Field Description': 'Water & Electricity (must)', 'Field Name': 'LocalWaterElectricity', 'Field Default Value': 3000, 'Field Input': ''},
    {'Field Description': 'Insurance - Car & bike (must)', 'Field Name': 'LocalInsuranceVehicle', 'Field Default Value': 2000, 'Field Input': ''},
    {'Field Description': 'Property Tax (must)', 'Field Name': 'LocalPropertyTax', 'Field Default Value': 1000, 'Field Input': ''},
    {'Field Description': 'Medical Insurance (must)', 'Field Name': 'LocalMedicalInsurance', 'Field Default Value': 4500, 'Field Input': ''},
    {'Field Description': 'Transport - Fuel (must)', 'Field Name': 'LocalTransportFuel', 'Field Default Value': 10000, 'Field Input': ''},
    {'Field Description': 'Vehicle Maintenance (must)', 'Field Name': 'LocalVehicleMaintenance', 'Field Default Value': 1000, 'Field Input': ''},
    {'Field Description': 'House Repairs (must)', 'Field Name': 'LocalHouseRepairs', 'Field Default Value': 1250, 'Field Input': ''},
    {'Field Description': 'Maid services (must)', 'Field Name': 'LocalMaidServices', 'Field Default Value': 5000, 'Field Input': ''},
    {'Field Description': 'Entertainment ( movies , eating) (must)', 'Field Name': 'LocalEntertainment', 'Field Default Value': 10000, 'Field Input': ''},
    {'Field Description': 'Internet,Mobile (must)', 'Field Name': 'LocalInternetMobileTelecom', 'Field Default Value': 2000, 'Field Input': ''},
    {'Field Description': 'TV- OTT , Cable (must)', 'Field Name': 'LocalTVOTT', 'Field Default Value': 1250, 'Field Input': ''},
    {'Field Description': 'Travel & leisure - inland (must)', 'Field Name': 'LocalTravelLeisureInland', 'Field Default Value': 15000, 'Field Input': ''},
    {'Field Description': 'Miscellaneous (SWP - LTCG (>1 lac) Tax)', 'Field Name': 'LocalMiscellaneousTax', 'Field Default Value': 1335, 'Field Input': ''},
    {'Field Description': 'Functions Etc', 'Field Name': 'LocalFunctionsEtc', 'Field Default Value': 1000, 'Field Input': ''},
    {'Field Description': 'Total Yearly Expenses - must', 'Field Name': 'GLTotalYearlyExpensesMust', 'Field Default Value': '= {LocalGroceryVeg} + {LocalWaterElectricity} + {LocalInsuranceVehicle} + {LocalPropertyTax} + {LocalMedicalInsurance} + {LocalTransportFuel} + {LocalVehicleMaintenance} + {LocalHouseRepairs} + {LocalMaidServices} + {LocalEntertainment} + {LocalInternetMobileTelecom} + {LocalTVOTT} + {LocalTravelLeisureInland} + {LocalMiscellaneousTax} + {LocalFunctionsEtc}', 'Field Input': '= {LocalGroceryVeg} + {LocalWaterElectricity} + {LocalInsuranceVehicle} + {LocalPropertyTax} + {LocalMedicalInsurance} + {LocalTransportFuel} + {LocalVehicleMaintenance} + {LocalHouseRepairs} + {LocalMaidServices} + {LocalEntertainment} + {LocalInternetMobileTelecom} + {LocalTVOTT} + {LocalTravelLeisureInland} + {LocalMiscellaneousTax} + {LocalFunctionsEtc}'},
    {'Field Description': 'Travel & leisure - foreign (Occasional)- (Optional)', 'Field Name': 'LocalTravelLeisureForeignOpt', 'Field Default Value': 0, 'Field Input': ''},
    {'Field Description': 'Others - (Optional)', 'Field Name': 'LocalOthersOpt', 'Field Default Value': 0, 'Field Input': ''},
    {'Field Description': 'Total Yearly Expenses - Optional', 'Field Name': 'GLTotalYearlyExpensesOptional', 'Field Default Value': '={LocalTravelLeisureForeignOpt} + {LocalOthersOpt}', 'Field Input': '={LocalTravelLeisureForeignOpt} + {LocalOthersOpt}'}
]

INVESTMENT_PLAN_CONFIG = [
    {'Field Description': 'PF accumulation Amount', 'Field Name': 'LocalPFAmount', 'Field Value': '={GLPFAccumulation}'},
    {'Field Description': 'PPF accumulation Amount', 'Field Name': 'LocalPPFAmount', 'Field Value': '={GLPPFAccumulation}'},
    {'Field Description': 'Superannuation accumulation Amount', 'Field Name': 'LocalSuperannuationAmount', 'Field Value': '={GLSuperannuation}'},
    {'Field Description': 'Starting Total Available Corpus to Invest', 'Field Name': 'LocalStartingCorpus', 'Field Value': '={LocalPFAmount}+{LocalPPFAmount}+{LocalSuperannuationAmount}'},
    {'Field Description': 'FDs Percentage of Total Corpus', 'Field Name': 'LocalDebtFdsPercent', 'Field Value': '={GLNonSWPInvestmentPercentage}'},
    {'Field Description': 'SWP Percentage of Total Corpus', 'Field Name': 'LocalSWPPercent', 'Field Value': '={GLSWPInvestmentPercentage}'},
    {'Field Description': 'investmentatrisk(withSWP)', 'Field Name': 'LocalSWPInvestAmount', 'Field Value': '={LocalStartingCorpus}*({LocalSWPPercent}/100)'},
    {'Field Description': 'SWP Avg Annual return rate', 'Field Name': 'LocalSWPGrowthRate', 'Field Value': '={GLSWPGrowthRate}'},
    {'Field Description': 'SWP Avg Monthly Return rate', 'Field Name': 'LocalSWPMonthlyRate', 'Field Value': '={GLSWPMonthlyRate}'},
    {'Field Description': 'SWP monthly withdrawal', 'Field Name': 'LocalSWPMonthlyWithdrawal', 'Field Value': '={GLSWPMonthlyWithdrawal}'},
    {'Field Description': 'SWP LCTG slab', 'Field Name': 'LocalSWPLCTGTaxSlab', 'Field Value': '={GLSWPLCTGTaxSlab}'},
    {'Field Description': 'SWP LCTG exemption', 'Field Name': 'LocalSWPLCTGExemption', 'Field Value': '={GLSWPLCTGExemption}'},
    {'Field Description': 'FD Investment Fund with guaranteed corpus', 'Field Name': 'LocalFDInvestmentFund', 'Field Value': '={LocalStartingCorpus}*({LocalDebtFdsPercent}/100)'},
    {'Field Description': 'Normal FD percentage', 'Field Name': 'LocalNormalFDPercent', 'Field Value': '={GLNormalFDExcludingPOMISSCSS}'},
    {'Field Description': 'Sr Citizen FD ( 100% - Normal FD)', 'Field Name': 'LocalSrCitizenFDPercent', 'Field Value': '={GLSrCitizenFDExcludingPOMISSCSS}'},
    {'Field Description': 'SCSS Amount', 'Field Name': 'LocalSCSSAmount', 'Field Value': '={GLSCSSSingle}'},
    {'Field Description': 'POMIS Amount', 'Field Name': 'LocalPOMISAmount', 'Field Value': '={GLPOMISSingle}'},
    {'Field Description': 'Investment CalculationsYearlySWP Intended Withdrawal Yearly', 'Field Name': 'LocalSWPYearlyWithdrawal', 'Field Value': '={GLSWPMonthlyWithdrawal} * 12'},
    {'Field Description': 'SWP Interest earned Yearly', 'Field Name': 'LocalSWPYearlyInterest', 'Field Value': '={LocalSWPInvestAmount}*(1+{LocalSWPMonthlyRate})**12-{LocalSWPInvestAmount}'},
    {'Field Description': 'SWP Corpus Balance Post Withdrawal Yearwise', 'Field Name': 'LocalSWPBalancePostWithdrawal', 'Field Value': '={LocalSWPInvestAmount}+{LocalSWPYearlyInterest}-{LocalSWPYearlyWithdrawal}'},
    {'Field Description': 'SWP Corpus depletion/increase (depending on market)', 'Field Name': 'GLSWPCorpusStatus', 'Field Value': '={LocalSWPBalancePostWithdrawal}-{LocalSWPInvestAmount}'},
    {'Field Description': 'Income from Normal FD Yearly', 'Field Name': 'LocalNormalFDYearlyIncome', 'Field Value': '=(({LocalFDInvestmentFund}-{LocalSCSSAmount}-{LocalPOMISAmount})*({LocalNormalFDPercent}/100))*({GLNormalFDRate}/100)'},
    {'Field Description': 'Income from Senior citizen FD - First Five Years', 'Field Name': 'LocalSrFDYearlyIncomeFirst5', 'Field Value': '=(({LocalFDInvestmentFund}-{LocalSCSSAmount}-{LocalPOMISAmount})*({LocalSrCitizenFDPercent}/100))*({GLSrCitizenFDRate}/100)'},
    {'Field Description': 'Income from POMIS Yealry', 'Field Name': 'LocalPOMISYearlyIncome', 'Field Value': '={GLPOMISSingle} * ({GLPOMISRate}/100)'},
    {'Field Description': 'Income from Senior Citizen Savings Scheme (SCSS)', 'Field Name': 'LocalSCSSYearlyIncome', 'Field Value': '={GLSCSSSingle} * ({GLSCSSRate}/100)'},
    {'Field Description': 'Senior citizen FD - Six Onward Years', 'Field Name': 'LocalSrFDYearlyIncomePast5', 'Field Value': '=(({LocalSrFDYearlyIncomeFirst5}+{LocalPOMISYearlyIncome}+{LocalSCSSYearlyIncome})*({GLNormalFDRate}/100))'},
    {'Field Description': 'Rental income ( MAX limit 30000)', 'Field Name': 'LocalRentalIncome', 'Field Value': '={GLCurrentMonthlyRental}*12'},
    {'Field Description': 'Divident Income - existing shares - yearly ( based on portfolio)', 'Field Name': 'LocalDividentIncome', 'Field Value': '={GLDividendIncome}'},
    {'Field Description': 'Agriculture Income - existing- In Place', 'Field Name': 'LocalAgricultureIncome', 'Field Value': '={GLAgricultureIncome}'},
    {'Field Description': 'Annuity Existing (LIC, HDFC Etc)', 'Field Name': 'LocalAnnuityExisting', 'Field Value': '={GLAnnuityExistingMonthly}*12'},
    {'Field Description': 'Annuity New (PPF VPF Superannuation NPS etc)', 'Field Name': 'LocalAnnuityNew', 'Field Value': '={GLAnnuityNew}*12'},
    {'Field Description': 'Others EPS Pension', 'Field Name': 'LocalPensionEPS', 'Field Value': '={GLPensionEPS}*12'},
    {'Field Description': 'Others Income Source - Variable At Risk - Share Trading', 'Field Name': 'LocalTradingIncome', 'Field Value': '={GLTradingIncome}'},
    {'Field Description': 'Land Flat - Buy & Sell', 'Field Name': 'LocalRealStateIncome', 'Field Value': '={GLRealStateIncome}'},
    {'Field Description': 'Consulting Jobs income', 'Field Name': 'LocalConsultingIncome', 'Field Value': '={GLConsultingIncome}*12'},
    {'Field Description': 'Total Yearly Income from All Sources', 'Field Name': 'GLTotalIncomeOverallFDs', 'Field Value': '={LocalNormalFDYearlyIncome}+{LocalSrFDYearlyIncomeFirst5}+{LocalPOMISYearlyIncome}+{LocalSCSSYearlyIncome}+{LocalSrFDYearlyIncomePast5}+{LocalRentalIncome}+{LocalDividentIncome}+{LocalAgricultureIncome}+{LocalAnnuityExisting}+{LocalAnnuityNew}+{LocalPensionEPS}+{LocalTradingIncome}+{LocalRealStateIncome}+{LocalConsultingIncome}+{LocalSWPYearlyWithdrawal}+{GLSWPCorpusStatus}'}
]

KNOWLEDGEBASE_FAQ_DATA = [
    {'Investment Option': 'Regular Bank FD', 'Lock-in Period': '7 days to 10 years', 'Minimum Amount': '₹1,000 (varies by bank)', 'Frequency of Interest / Return': 'Monthly/Quarterly/Annually', 'Notes': 'Interest is taxable as per slab'},
    {'Investment Option': 'Tax Saving FD', 'Lock-in Period': '5 years', 'Minimum Amount': '₹100 or ₹1,000', 'Frequency of Interest / Return': 'Quarterly/Annually (Cumulative)', 'Notes': 'Eligible for 80C deduction, interest is taxable'},
    {'Investment Option': 'SCSS (Senior Citizens Savings Scheme)', 'Lock-in Period': '5 years (extendable by 3)', 'Minimum Amount': '₹1,000 (max ₹30L total)', 'Frequency of Interest / Return': 'Quarterly', 'Notes': 'Eligible for 80C, interest taxable, but TDS only if > ₹50,000 p.a.'},
    {'Investment Option': 'POMIS (Post Office Monthly Income)', 'Lock-in Period': '5 years', 'Minimum Amount': '₹1,000 (max ₹9L/single)', 'Frequency of Interest / Return': 'Monthly', 'Notes': 'Interest taxable, no 80C benefit'},
    {'Investment Option': 'Balanced MFs with SWP', 'Lock-in Period': 'No lock-in (except ELSS)', 'Minimum Amount': '₹500–₹1,000/month', 'Frequency of Interest / Return': 'As per SWP setup (Monthly etc.)', 'Notes': 'SWP returns may include capital gains — tax depends on equity/debt'},
    {'Investment Option': 'Equity/ Debt MFs', 'Lock-in Period': 'Equity: 1 year; Debt: 3 years', 'Minimum Amount': '₹500 onwards', 'Frequency of Interest / Return': 'Growth or Dividend (if opted)', 'Notes': 'LTCG tax rules apply post holding period'},
    {'Investment Option': 'Senior Citizen FDs', 'Lock-in Period': '7 days to 10 years', 'Minimum Amount': '₹1,000–₹5,000', 'Frequency of Interest / Return': 'Monthly/Quarterly/Annually', 'Notes': 'Higher interest than regular FDs; taxable'},
    {'Investment Option': 'Annuity Plans (LIC/HDFC/SBI Life)', 'Lock-in Period': 'Lifetime or selected tenure', 'Minimum Amount': '₹1 lakh to ₹10 lakh+', 'Frequency of Interest / Return': 'Monthly/Quarterly/Yearly', 'Notes': 'Annuity is taxable; no 80C on annuity payout'},
    {'Investment Option': 'NSC (National Savings Certificate)', 'Lock-in Period': '5 years', 'Minimum Amount': '₹1,000 (no max limit)', 'Frequency of Interest / Return': 'Interest reinvested annually', 'Notes': '80C benefit; interest taxable but deemed reinvested (compound)'}
]