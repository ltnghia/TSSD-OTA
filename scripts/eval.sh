type='conf_conv_lstm'
video_name='/home/sean/data/ILSVRC/Data/VID/snippets/val/ILSVRC2017_val_00331000.mp4'
conf_thresh=0.01
nms_thresh=0.45
top_k=200
set_file_name='val'
detection='yes'
if [ $type = 'ssd' ]
then
    pythonc3 ../eval.py \
    --model_dir '../weights/ssd300_VID2017' \
    --model_name ssd300 \
    --literation 280000 \
    --save_folder ../eval \
    --confidence_threshold $conf_thresh \
    --nms_threshold $nms_thresh \
    --top_k $top_k \
    --ssd_dim 300 \
    --set_file_name $set_file_name \
    --dataset_name 'VID2017' \
    --tssd $type \
    --detection $detection
elif [ $type = 'conf_conv_lstm' ]
then
    pythonc3 ../eval.py \
    --model_dir '../weights/tssd300_VID2017_b4_s16_conf_preVggExtra' \
    --model_name ssd300 \
    --literation 10000 \
    --save_folder ../eval \
    --confidence_threshold $conf_thresh \
    --nms_threshold $nms_thresh \
    --top_k $top_k \
    --ssd_dim 300 \
    --set_file_name $set_file_name \
    --dataset_name 'seqVID2017' \
    --tssd $type \
    --detection $detection
elif [ $type = 'both_conv_lstm' ]
then
    pythonc3 ../eval.py \
    --model_dir '../weights/tssd300_VID2017_b2_s16_both_preVggExtra' \
    --model_name ssd300 \
    --literation 10000 \
    --save_folder ../eval \
    --confidence_threshold $conf_thresh \
    --nms_threshold $nms_thresh \
    --top_k $top_k \
    --ssd_dim 300 \
    --set_file_name $set_file_name \
    --dataset_name 'seqVID2017' \
    --tssd $type \
    --detection $detection
fi