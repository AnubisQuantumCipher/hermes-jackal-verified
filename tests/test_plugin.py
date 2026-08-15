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
        self.assertEqual(len(ctx.tools),10)
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

    def test_package_identity_poison_fails_admission(self):
        # v2: a wrong pinned package tarball hash must refuse admission before
        # any binary runs (the package, not a single binary, is the trust root).
        original=tools.PKG_SHA256
        tools._ADMITTED=None
        tools.PKG_SHA256="0"*64
        try:
            body=call(tools.evaluate,{'expression':'2+2'})
            self.assertFalse(body['success']); self.assertIn('mismatch',body['error'])
        finally:
            tools.PKG_SHA256=original; tools._ADMITTED=None

    def test_admitted_snapshot_is_private_and_pinned(self):
        # v2: admission yields a private snapshot whose evaluator+checker match
        # the pinned identities and live outside the plugin tree.
        tools._ADMITTED=None
        adm=tools._admit_package()
        self.assertEqual(tools._sha(Path(adm['evaluator'])),tools.APPROVED_SHA256)
        self.assertEqual(tools._sha(Path(adm['checker'])),tools.APPROVED_CHECKER_SHA256)
        self.assertNotIn(str(tools.PLUGIN_ROOT),adm['evaluator'])
        # non-formal lane runs from the admitted snapshot and releases
        raw=tools._invoke(['eval','2+2'])
        self.assertTrue(raw['released'])

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

    def test_gaussian_lane_round_trips(self):
        body=call(tools.gaussian_integral,{
            'expression':'exp(-10000000000*(x-0.5000123456789)^2)',
            'lower':0,'upper':1,'tolerance':'1/1000'})
        result=body['receipt']['result']
        self.assertEqual(result['status'],'formal-bounded'); self.assertEqual(result['variant'],'gaussian')
        self.assertEqual(result['theorem'],tools.GAUSSIAN_THEOREM)
        ver=tools.verify(body['receipt']); self.assertTrue(ver['valid'], ver.get('errors'))

    def test_sqrt_rat_lane_round_trips(self):
        body=call(tools.sqrt_rat_bound,{'expression':'sqrt(x)','lower':'2','upper':'3'})
        result=body['receipt']['result']
        self.assertEqual(result['status'],'formal-bounded'); self.assertEqual(result['variant'],'sqrt_rat')
        self.assertEqual(result['theorem'],tools.FORMAL_THEOREM)
        ver=tools.verify(body['receipt']); self.assertTrue(ver['valid'], ver.get('errors'))

    def test_exp_rat_lane_round_trips(self):
        body=call(tools.exp_rat_bound,{'expression':'exp(x)','lower':'0','upper':'1'})
        result=body['receipt']['result']
        self.assertEqual(result['status'],'formal-bounded'); self.assertEqual(result['variant'],'exp_rat')
        self.assertEqual(result['theorem'],tools.FORMAL_THEOREM)
        ver=tools.verify(body['receipt']); self.assertTrue(ver['valid'], ver.get('errors'))

    def test_variant_bindings_are_load_bearing(self):
        # Every variant re-check must refuse if we tamper with theorem, variant,
        # producer identity, or cross-swap a certificate.
        for op_name in ('gaussian_integral','sqrt_rat_bound','exp_rat_bound'):
            with self.subTest(op=op_name):
                if op_name=='gaussian_integral':
                    body=call(getattr(tools,op_name),{'expression':'exp(-10000000000*(x-0.5000123456789)^2)',
                                                       'lower':0,'upper':1,'tolerance':'1/1000'})
                elif op_name=='sqrt_rat_bound':
                    body=call(getattr(tools,op_name),{'expression':'sqrt(x)','lower':'2','upper':'3'})
                else:
                    body=call(getattr(tools,op_name),{'expression':'exp(x)','lower':'0','upper':'1'})
                base=body['receipt']
                # Baseline verifies
                self.assertTrue(tools.verify(base)['valid'], tools.verify(base).get('errors'))
                for mut in (
                    lambda t: t['result'].__setitem__('theorem','nope'),
                    lambda t: t['result'].__setitem__('variant','range'),
                    lambda t: t['instrument']['evaluator'].__setitem__('sha256','b'*64),
                    lambda t: t['instrument']['checker'].__setitem__('sha256','c'*64),
                    lambda t: t['result'].__setitem__('enclosure',{'lower':'0','upper':'0'}),
                    lambda t: t['result'].__setitem__('certificate_sha256','d'*64),
                    lambda t: t['result'].__setitem__('cert_status','oops'),
                ):
                    import copy
                    tampered=copy.deepcopy(base); mut(tampered); resign(tampered)
                    self.assertFalse(tools.verify(tampered)['valid'], f'{op_name} verify did not refuse')


if __name__=='__main__': unittest.main(verbosity=2)
