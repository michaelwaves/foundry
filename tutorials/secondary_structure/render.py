from pymol import cmd

TYPE = "beta"

if TYPE == "alpha":
    cmd.fab("EAAAKEAAAKEAAAKEAAAKEAAAKEAAAKEAAAKEAAAK", "helix", ss=1)
else:
    cmd.fetch("1pgb")
    cmd.hide("everything")
    cmd.show("cartoon")
    cmd.select("hairpin", "resi 41-56")
    cmd.zoom("hairpin")
    # cmd.fab("VTVTVTVTVTVTVTVTNPGTVTVTVTVTVTVTVTVTVTVT", "beta_peptide", ss=2)

cmd.bg_color("white")
cmd.show("cartoon")
cmd.orient()
cmd.ray(1600, 1200)   # high-quality render

if TYPE == "alpha":
    cmd.png("alpha.png", dpi=300)
else:
    cmd.png("beta.png", dpi=300)
