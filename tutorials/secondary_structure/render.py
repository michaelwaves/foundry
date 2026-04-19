from pymol import cmd

TYPE = "alpha"

cmd.fetch("1pgb")
cmd.hide("everything")

if TYPE == "alpha":
    # cmd.fab("EAAAKEAAAKEAAAKEAAAKEAAAKEAAAKEAAAKEAAAK", "helix", ss=1)
    cmd.select("helix", "resi 23-36")
    cmd.show("cartoon", "helix")
    cmd.orient("helix")
    cmd.zoom("helix")
else:
    cmd.select("sheet_s1", "resi 12-20+1-9+50-56+42-46")
    cmd.show("line", "sheet_s1")
    # cmd.color("salmon",    "resi 12-20")
    # cmd.color("skyblue",   "resi 1-9")
    # cmd.color("palegreen", "resi 50-56")
    # cmd.color("lightpink", "resi 42-46")
    cmd.orient("sheet_s1")
    cmd.zoom("sheet_s1")
    # cmd.fab("VTVTVTVTVTVTVTVTNPGTVTVTVTVTVTVTVTVTVTVT", "beta_peptide", ss=2)

cmd.bg_color("white")
cmd.ray(1600, 1200)   # high-quality render

if TYPE == "alpha":
    cmd.png("alpha.png", dpi=300)
else:
    cmd.png("beta_line.png", dpi=300)
