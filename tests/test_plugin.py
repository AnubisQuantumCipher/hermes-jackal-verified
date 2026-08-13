#!/usr/bin/env python3
from __future__ import annotations
import hashlib, importlib.util, json, os, shutil, stat, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('jackal_tools',ROOT/'tools.py')
tools=importlib.util.module_from_spec(spec); spec.loader.exec_module(tools)


class FakeContext:
    def __init__(self):
        self.tools=[]; self.skills=[]; self.sections=[]
    def get_config(self, _name, default=None): return default
    def register_tool(self, **kwargs): self.tools.append(kwargs)
    def register_skill(self, name, path): self.skills.append((name,Path(path)))
    def register_system_prompt_section(self, section_id, content, **kwargs): self.sections.append((section_id,content,kwargs))


def call(fn,args):
    return json.loads(fn(args))


def resign(receipt):
    import hashlib
    core={k:receipt[k] for k in ('schema','operation','request','result','instrument')}
    receipt['receipt_sha256']=hashlib.sha256(tools._canonical(core)).hexdigest()
    return receipt


class JackalPluginTests(unittest.TestCase):
    def test_plugin_registers_tools_skill_and_automatic_routing(self):
        package=importlib.util.spec_from_file_location(
            'jackal_verified', ROOT/'__init__.py',
            submodule_search_locations=[str(ROOT)],
        )
        module=importlib.util.module_from_spec(package)
        sys.modules[package.name]=module
        try: package.loader.exec_module(module)
        finally: sys.modules.pop(package.name,None)
        ctx=FakeContext(); module.register(ctx)
        self.assertEqual(len(ctx.tools),7)
        self.assertEqual([name for name,_ in ctx.skills],['jackal-verified-computation'])
        self.assertTrue(ctx.skills[0][1].is_file())
        self.assertEqual(ctx.sections[0][0],'jackal-verified.routing')
        self.assertIn('Never silently downgrade',ctx.sections[0][1])

    def test_exact_rational_and_receipt(self):
        body=call(tools.exact,{'mode':'rational','expression':'0.1+0.2'})
        receipt=body['receipt']; self.assertEqual(receipt['result']['status'],'exact'); self.assertEqual(receipt['result']['exact'],'3/10')
        self.assertTrue(tools.verify(receipt)['valid'])

    def test_huge_integer_full_output(self):
        body=call(tools.exact,{'mode':'big_power','a':'2','b':'10000'})
        self.assertEqual(body['receipt']['result']['digits'],3011)
        self.assertTrue(tools.verify(body['receipt'])['valid'])

    def test_checked_derivative(self):
        body=call(tools.differentiate,{'expression':'x^(x^x)'})
        self.assertEqual(body['receipt']['result']['status'],'checked')
        self.assertIn('not a proof',body['receipt']['result']['non_claims'][0])

    def test_bounded_spike_and_no_downgrade(self):
        args={'expression':'exp(0-100000000*(x-0.1234567)^2)','lower':0,'upper':1,'assurance':'bounded','tolerance':1e-8}
        body=call(tools.integrate,args); result=body['receipt']['result']
        self.assertEqual(result['status'],'bounded'); self.assertLessEqual(result['enclosure']['width'],1e-8*(1+1e-9))
        self.assertTrue(tools.verify(body['receipt'])['valid'])

    def test_hazard_refusal_is_receipted(self):
        body=call(tools.range_bound,{'expression':'1/x','lower':-1,'upper':1})
        self.assertEqual(body['receipt']['result']['status'],'refused'); self.assertFalse(body['receipt']['result']['released'])
        self.assertTrue(tools.verify(body['receipt'])['valid'])

    def test_claim_card_fingerprint_recomputed(self):
        body=call(tools.claim_card,{'model':'projectile','speed':20,'angle_degrees':45,'gravity':9.80665})
        result=body['receipt']['result']; self.assertEqual(result['status'],'model-based'); self.assertTrue(result['fingerprint_recomputed'])
        self.assertTrue(tools.verify(body['receipt'])['valid'])

    def test_tampered_receipt_fails(self):
        receipt=call(tools.exact,{'mode':'rational','expression':'1/3'})['receipt']
        receipt['result']['exact']='2/3'
        verdict=tools.verify(receipt); self.assertFalse(verdict['valid']); self.assertIn('receipt digest mismatch',verdict['errors'])

    def test_reversed_enclosure_fails_even_with_recomputed_digest(self):
        receipt=call(tools.integrate,{'expression':'x^2','lower':0,'upper':1,'assurance':'bounded','tolerance':1e-7})['receipt']
        receipt['result']['enclosure']['lower']='2'; receipt['result']['enclosure']['upper']='1'
        core={k:receipt[k] for k in ('schema','operation','request','result','instrument')}
        import hashlib
        receipt['receipt_sha256']=hashlib.sha256(tools._canonical(core)).hexdigest()
        self.assertIn('reversed enclosure',tools.verify(receipt)['errors'])

    def test_binary_identity_poison_fails_before_execution(self):
        original=tools.BINARY
        with tempfile.TemporaryDirectory() as td:
            poison=Path(td)/'jackal'; poison.write_text('#!/bin/sh\nprintf 42\\n'); poison.chmod(0o700)
            tools.BINARY=poison
            try:
                body=call(tools.evaluate,{'expression':'2+2'})
                self.assertFalse(body['success']); self.assertIn('identity mismatch',body['error'])
            finally: tools.BINARY=original

    def test_private_snapshot_resists_public_path_a_b_a_substitution(self):
        original_binary,original_digest,original_run=tools.BINARY,tools.APPROVED_SHA256,tools.subprocess.run
        with tempfile.TemporaryDirectory() as td:
            public=Path(td)/'jackal-native'
            admitted=b'#!/bin/sh\nprintf A\\n\n'; substitute=b'#!/bin/sh\nprintf B\\n\n'
            public.write_bytes(admitted); public.chmod(0o700)
            seen={}
            def fake_run(argv,**kwargs):
                snapshot=Path(argv[0])
                seen['private_path']=snapshot!=public and snapshot.parent!=public.parent
                seen['snapshot_was_admitted']=snapshot.read_bytes()==admitted
                public.write_bytes(substitute); public.chmod(0o700)
                seen['public_substituted']=public.read_bytes()==substitute
                public.write_bytes(admitted); public.chmod(0o700)
                return subprocess.CompletedProcess(argv,0,stdout='4\n',stderr='')
            tools.BINARY=public; tools.APPROVED_SHA256=hashlib.sha256(admitted).hexdigest(); tools.subprocess.run=fake_run
            try:
                raw=tools._invoke(['eval','2+2'])
                self.assertTrue(raw['released'])
                self.assertTrue(all(seen.values()))
                self.assertEqual(public.read_bytes(),admitted)
            finally:
                tools.BINARY,tools.APPROVED_SHA256,tools.subprocess.run=original_binary,original_digest,original_run

    def test_input_controls(self):
        self.assertFalse(call(tools.evaluate,{'expression':'\x00'})['success'])
        self.assertFalse(call(tools.evaluate,{'expression':'1+\n2'})['success'])
        self.assertFalse(call(tools.integrate,{'expression':'x','lower':1,'upper':0,'assurance':'bounded','tolerance':1e-6})['success'])
        self.assertFalse(call(tools.exact,{'mode':'big_multiply','a':'12x','b':'3'})['success'])
        self.assertFalse(call(tools.exact,{'mode':'big_power','a':'2','b':str(tools.MAX_EXPONENT+1)})['success'])

    def test_recomputed_digest_cannot_cross_operation_status(self):
        receipt=call(tools.exact,{'mode':'rational','expression':'1/3'})['receipt']
        receipt['operation']='jackal_evaluate'
        core={k:receipt[k] for k in ('schema','operation','request','result','instrument')}
        import hashlib
        receipt['receipt_sha256']=hashlib.sha256(tools._canonical(core)).hexdigest()
        verdict=tools.verify(receipt)
        self.assertFalse(verdict['valid'])
        self.assertIn('status is invalid for operation',verdict['errors'])

    def test_recomputed_digest_cannot_forge_required_semantics(self):
        cases=[]

        exact=call(tools.exact,{'mode':'rational','expression':'1/3'})['receipt']
        exact['result'].pop('exact'); cases.append((resign(exact),'malformed exact rational result'))

        refused=call(tools.range_bound,{'expression':'1/x','lower':-1,'upper':1})['receipt']
        refused['result']['released']=True; cases.append((resign(refused),'non-release status must set released=false'))

        checked=call(tools.differentiate,{'expression':'x^2'})['receipt']
        checked['result'].pop('check'); cases.append((resign(checked),'malformed derivative check metadata'))

        model=call(tools.claim_card,{'model':'projectile','speed':20,'angle_degrees':45,'gravity':9.80665})['receipt']
        model['request']['model']='other'; cases.append((resign(model),'claim-card model mismatch'))

        for receipt,error in cases:
            with self.subTest(error=error):
                verdict=tools.verify(receipt)
                self.assertFalse(verdict['valid'])
                self.assertIn(error,verdict['errors'])


if __name__=='__main__': unittest.main(verbosity=2)
