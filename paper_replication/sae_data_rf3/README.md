# 1 Collect Activations
collect_train.sh

# 2 Label Activatons
 detect labels inputs=tutorials/sae_data_rf3/label_acts.yaml out_dir=tutorials/sae_data_rf3/labels

 # 3 train logistic regression classifier
detect fit  inputs=tutorials/sae_data_rf3/block12_logistic.yaml out_dir=outputs/detect/rf3_block12_lr
 
 # 4 evaluate   
detect evaluate inputs=tutorials/sae_data_rf3/evaluate_block12_logistic.yaml out_dir=outputs/detect/rf3_block12_lr_eval