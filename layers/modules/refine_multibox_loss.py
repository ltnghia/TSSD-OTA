import torch
import torch.nn as nn
import torch.nn.functional as F
from ..box_utils import match, log_sum_exp, refine_match

class RefineMultiBoxLoss(nn.Module):

    def __init__(self, num_classes, overlap_thresh, prior_for_matching,
                 bkg_label, neg_mining, neg_pos, neg_overlap, encode_target,
                 object_score=0.01, device=torch.device('cpu')):
        super(RefineMultiBoxLoss, self).__init__()
        self.device = device
        self.num_classes = num_classes
        self.threshold = overlap_thresh
        self.background_label = bkg_label
        self.encode_target = encode_target
        self.use_prior_for_matching = prior_for_matching
        self.do_neg_mining = neg_mining
        self.negpos_ratio = neg_pos
        self.neg_overlap = neg_overlap
        self.object_score = object_score
        self.variance = [0.1, 0.2]

    def forward(self, prediction, priors, targets, arm_data=None, filter_object=False):

        loc_data, conf_data = prediction
        if arm_data:
            arm_loc, arm_conf = arm_data
        num = loc_data.size(0) # batch
        num_priors = priors.size(0)
        # num_classes = self.num_classes

        # match priors (default boxes) and ground truth boxes
        loc_t = torch.Tensor(num, num_priors, 4)
        conf_t = torch.LongTensor(num, num_priors)

        for idx in range(num):
            truths = targets[idx][:, :-1]
            labels = targets[idx][:, -1]
            defaults = priors
            if self.num_classes == 2:
                labels = labels > 0
            if arm_data:
                refine_match(self.threshold, truths, defaults, self.variance, labels, loc_t, conf_t, idx,
                             arm_loc[idx])
            else:
                match(self.threshold, truths, defaults, self.variance, labels, loc_t, conf_t, idx)
        with torch.no_grad():
            loc_t = loc_t.to(self.device)
            conf_t = conf_t.to(self.device)

        if arm_data and filter_object:
            arm_conf_data = arm_conf[:, :, 1]
            pos = conf_t > 0
            object_score_index = arm_conf_data <= self.object_score
            pos[object_score_index] = 0
        else:
            pos = conf_t > 0

        # Localization Loss (Smooth L1)
        # Shape: [batch,num_priors,4]
        pos_idx = pos.unsqueeze(pos.dim()).expand_as(loc_data)
        loc_p = loc_data[pos_idx].view(-1, 4)
        loc_t = loc_t[pos_idx].view(-1, 4)
        loss_l = F.smooth_l1_loss(loc_p, loc_t, size_average=False)

        # Compute max conf across batch for hard negative mining
        batch_conf = conf_data.view(-1, self.num_classes)
        loss_c = log_sum_exp(batch_conf) - batch_conf.gather(1, conf_t.view(-1, 1))

        # Hard Negative Mining
        loss_c[pos.view(-1, 1)] = 0  # filter out pos boxes for now
        loss_c = loss_c.view(num, -1)
        _, loss_idx = loss_c.sort(1, descending=True)
        _, idx_rank = loss_idx.sort(1)
        num_pos = pos.long().sum(1, keepdim=True)
        num_neg = torch.clamp(self.negpos_ratio*num_pos, max=pos.size(1)-1)
        neg = idx_rank < num_neg.expand_as(idx_rank)

        # Confidence Loss Including Positive and Negative Examples
        pos_idx = pos.unsqueeze(2).expand_as(conf_data)
        neg_idx = neg.unsqueeze(2).expand_as(conf_data)
        conf_p = conf_data[(pos_idx+neg_idx).gt(0)].view(-1, self.num_classes)
        targets_weighted = conf_t[(pos+neg).gt(0)]
        loss_c = F.cross_entropy(conf_p, targets_weighted, size_average=False)

        # Sum of losses: L(x,c,l,g) = (Lconf(x, c) + αLloc(x,l,g)) / N

        N = num_pos.sum().float()
        loss_l /=  N
        loss_c /=  N
        return loss_l, loss_c

