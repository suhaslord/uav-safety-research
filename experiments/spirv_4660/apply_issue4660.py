#!/usr/bin/env python3
from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise SystemExit(f"expected exactly one match in {path}, found {text.count(old)}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


replace_once(
    "source/val/validate_group.cpp",
    """spv_result_t ValidateGroupAsyncCopy(ValidationState_t& _,\n                                    const Instruction* inst) {\n  if (_.FindDef(inst->type_id())->opcode() != spv::Op::OpTypeEvent) {\n""",
    """spv_result_t ValidateGroupAsyncCopy(ValidationState_t& _,\n                                    const Instruction* inst) {\n  if (auto error =\n          ValidateExecutionScope(_, inst, inst->GetOperandAs<uint32_t>(2))) {\n    return error;\n  }\n\n  if (_.FindDef(inst->type_id())->opcode() != spv::Op::OpTypeEvent) {\n""",
)

replace_once(
    "source/val/validate_group.cpp",
    """spv_result_t ValidateGroupWaitEvents(ValidationState_t& _,\n                                     const Instruction* inst) {\n  const uint32_t num_events_id = _.GetOperandTypeId(inst, 1);\n""",
    """spv_result_t ValidateGroupWaitEvents(ValidationState_t& _,\n                                     const Instruction* inst) {\n  if (auto error =\n          ValidateExecutionScope(_, inst, inst->GetOperandAs<uint32_t>(0))) {\n    return error;\n  }\n\n  const uint32_t num_events_id = _.GetOperandTypeId(inst, 1);\n""",
)

replace_once(
    "source/val/validate_scopes.cpp",
    """  // TODO(atgoo@github.com) Add checks for OpenCL and OpenGL environments.\n\n  // General SPIRV rules\n""",
    """  // OpenCL specific rules.\n  if (spvIsOpenCLEnv(_.context()->target_env) &&\n      (opcode == spv::Op::OpGroupAsyncCopy ||\n       opcode == spv::Op::OpGroupWaitEvents) &&\n      value != spv::Scope::Workgroup) {\n    return _.diag(SPV_ERROR_INVALID_DATA, inst)\n           << spvOpcodeString(opcode)\n           << ": in OpenCL environment Execution Scope must be Workgroup";\n  }\n\n  // TODO(atgoo@github.com) Add checks for OpenGL environments.\n\n  // General SPIRV rules\n""",
)

replace_once(
    "test/val/val_group_test.cpp",
    """TEST_F(ValidateGroup, GroupWaitEventsNumEvents) {\n""",
    """TEST_F(ValidateGroup, AsyncCopyOpenCLExecutionScopeMustBeWorkgroup) {\n  const std::string ss = R\"(\n      %a = OpGroupAsyncCopy %event %uint_1 %workgroup_float_var %cross_float_var %uint64_1 %uint64_1 %null_event\n  )\";\n  CompileSuccessfully(GenerateShaderCode(ss), SPV_ENV_OPENCL_2_0);\n  EXPECT_EQ(SPV_ERROR_INVALID_DATA,\n            ValidateInstructions(SPV_ENV_OPENCL_2_0));\n  EXPECT_THAT(\n      getDiagnosticString(),\n      HasSubstr(\"GroupAsyncCopy: in OpenCL environment Execution Scope must \"\n                \"be Workgroup\"));\n}\n\nTEST_F(ValidateGroup, GroupWaitEventsNumEvents) {\n""",
)

replace_once(
    "test/val/val_group_test.cpp",
    """TEST_F(ValidateGroup, GroupWaitEventsEventList) {\n""",
    """TEST_F(ValidateGroup, GroupWaitEventsOpenCLExecutionScopeMustBeWorkgroup) {\n  const std::string ss = R\"(\n    %a = OpVariable %func_event_ptr Function\n    OpGroupWaitEvents %uint_1 %uint_1 %a\n  )\";\n  CompileSuccessfully(GenerateShaderCode(ss), SPV_ENV_OPENCL_2_0);\n  EXPECT_EQ(SPV_ERROR_INVALID_DATA,\n            ValidateInstructions(SPV_ENV_OPENCL_2_0));\n  EXPECT_THAT(\n      getDiagnosticString(),\n      HasSubstr(\"GroupWaitEvents: in OpenCL environment Execution Scope must \"\n                \"be Workgroup\"));\n}\n\nTEST_F(ValidateGroup, GroupWaitEventsEventList) {\n""",
)
