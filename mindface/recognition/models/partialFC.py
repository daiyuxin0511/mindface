# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ============================================================================

import mindspore.nn as nn
from mindspore import Parameter
import mindspore.ops as ops
from mindspore import dtype as mstype
from mindspore.ops import functional as F
from mindspore.common.initializer import initializer

import sys
sys.path.append("mindface/recognition")
sys.path.append("recognition")

from loss.arcface_loss import ArcFace
from loss.ce_loss import SoftMaxCE

__all__=["PartialFC"]

class PartialFC(nn.Cell):
    '''
    partialFC
    '''
    def __init__(self, num_classes, world_size):
        super(PartialFC, self).__init__()
        self.L2Norm = ops.L2Normalize(axis=1)
        self.weight = Parameter(initializer(
            "normal", (num_classes, 512)), name="mp_weight")
        self.sub_weight = self.weight
        self.linear = ops.MatMul(transpose_b=True).shard(
            ((1, 1), (world_size, 1)))
        self.margin_softmax = ArcFace(world_size=world_size)
        self.loss = SoftMaxCE(world_size=world_size)

    def construct(self, features, label):
        total_label, norm_weight = self.prepare(label)
        total_features = self.L2Norm(features)
        logits = self.forward(total_features, norm_weight)
        logits = self.margin_softmax(logits, total_label)
        loss_v = self.loss(logits, total_label)
        return loss_v

    def forward(self, total_features, norm_weight):
        logits = self.linear(F.cast(total_features, mstype.float16), F.cast(
            norm_weight, mstype.float16))
        return F.cast(logits, mstype.float32)

    def prepare(self, label):
        total_label = label
        norm_weight = self.L2Norm(self.sub_weight)
        return total_label, norm_weight
