from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import numpy as np

import caffe2.python.fakelowp.init_shared_libs  # noqa
import time
from caffe2.proto import caffe2_pb2
from caffe2.python import core
from caffe2.python import workspace
from caffe2.python.onnx.onnxifi import onnxifi_caffe2_net
from caffe2.python.onnx.tests.test_utils import TestCase
from caffe2.python.fakelowp.test_utils import print_test_debug_info
from hypothesis import given, settings
from hypothesis import strategies as st
import caffe2.python.serialized_test.serialized_test_util as serial

core.GlobalInit(["caffe2",
                 "--glow_global_fp16=1",
                 "--glow_global_fused_scale_offset_fp16=1",
                 "--glow_global_force_sls_fp16_accum=1"])

GLOW_LOWERED_BATCHNORM = False


# Test the lowered LayerNorm op
class LayerNorm(serial.SerializedTestCase):
    @given(seed=st.integers(0, 65535),
        size = st.integers(2,8),
        input_channels=st.integers(1, 4),
        batch_size=st.integers(2,8),
        epsilon=st.floats(min_value=1e-5, max_value=1e-2))
    @settings(max_examples=100)
    def test_layernorm(self, seed, size, input_channels, batch_size, epsilon):
        np.random.seed(seed)
        # Reset the workspace
        workspace.ResetWorkspace()

        pred_net = caffe2_pb2.NetDef()
        pred_net.name = "pred"
        pred_net.external_input.extend(["X"])
        pred_net.external_output.extend(["Y", "mean", "rstd"])
        pred_net.op.add().CopyFrom(
            core.CreateOperator(
                "LayerNorm",
                ["X"],
                ["Y", "mean", "rstd"],
                # axis=-1,
                epsilon=epsilon
            )
        )

        pred_net_ref = caffe2_pb2.NetDef()
        pred_net_ref.name = "pred_ref"
        pred_net_ref.external_input.extend(["X"])
        pred_net_ref.external_output.extend(["Y", "mean", "rstd"])
        pred_net_ref.op.add().CopyFrom(
            core.CreateOperator(
                "LayerNormFakeFP16",
                ["X"],
                ["Y", "mean", "rstd"],
                # axis=-1,
                epsilon=epsilon
            )
        )

        X = np.random.rand(
            batch_size, input_channels, size, size).astype(np.float32) - 0.5

        pred_net_onnxified = onnxifi_caffe2_net(
            pred_net,
            {"X": [batch_size, input_channels, size, size]},
            debug=True,
            adjust_batch=False,
            use_onnx=False
        )
        num_onnxified_ops = sum(
            1 if o.type == "Onnxifi" else 0 for o in pred_net_onnxified.op)
        np.testing.assert_equal(num_onnxified_ops, 1)

        workspace.FeedBlob("X", X)

        workspace.CreateNet(pred_net)
        workspace.CreateNet(pred_net_ref)

        workspace.RunNet(pred_net_ref.name)
        Y_c2 = workspace.FetchBlob("Y")
        mean_c2 = workspace.FetchBlob("mean")
        std_c2 = workspace.FetchBlob("rstd")

        workspace.RunNet(pred_net.name)
        Y_glow = workspace.FetchBlob("Y")
        mean_glow = workspace.FetchBlob("mean")
        std_glow = workspace.FetchBlob("rstd")

        if not np.allclose(Y_glow.astype(np.float16), Y_c2.astype(np.float16)):
            diff_Y = np.abs(Y_glow - Y_c2).astype(np.float16)
            diff_std = np.abs(std_glow - std_c2).astype(np.float16)
            diff_mean = np.abs(mean_glow - mean_c2).astype(np.float16)
            print_test_debug_info(
                "layernorm",
                {
                    "seed": seed,
                    "size": size,
                    "input_channels": input_channels,
                    "batch_size": batch_size,
                    "epsilon": epsilon,
                    "X": X,
                    "Y_glow": Y_glow,
                    "mean_glow": mean_glow,
                    "std_glow": std_glow,
                    "Y_c2": Y_c2,
                    "mean_c2": mean_c2,
                    "std_c2": std_c2,     
                    "diff_Y": diff_Y,
                    "diff_mean": diff_mean,
                    "diff_std": diff_std,
                }
            )
            assert(0)
