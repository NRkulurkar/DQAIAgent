from synapse import load_dictionary

url = "https://dqsanavini.dfs.core.windows.net/dqcontainer/dictionary/DimSavingsAccount.csv"
rows = load_dictionary("pres.DimSavingsAccount", url)
print(f"Loaded {rows} rows for pres.DimSavingsAccount")