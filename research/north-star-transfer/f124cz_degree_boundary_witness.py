"""F124-CZ source-only algebraic nonrepresentability witness.

For Boolean functions, any degree<=2 GF(2) polynomial has identically
zero 3rd mixed finite derivative. Compute a third derivative of the
actual modular-carry author law at public zero input for ALL 16×16
hidden modular offsets. The additional hidden output XOR constant
cancels in the derivative. This proves the carry family cannot be
represented by the candidate's degree<=2 monomial basis, irrespective
of FIT optimizer, CHECK admission or heldout examples.

This checks a mathematical property of SOURCEFREE generated laws, not any
consumed original scientific source or private protected oracle.
"""
import json
import f124cz_outofclass_fixture as source

def derivative(order,model_values,mask,degree):
    result=0
    for subset in range(1<<degree):
        row=[0,0,0,0,0]
        for k,bit in enumerate(order):
            if subset>>k&1:
                row[bit//4]^=1<<(bit%4)
        result^=source.value(*model_values,*row,mask)
    return result

def carry_witness():
    tested=0
    for c0 in range(16):
        for c1 in range(16):
            value=derivative((0,1,8),
                 (source.REGIMES[1],),[c0,c1,0],3)
            if value==0:
                raise AssertionError("F124CZ_CARRY_NOT_PROVEN_OUTSIDE_DEGREE2")
            # XOR c2 constant has no effect on third derivative.
            changed=derivative((0,1,8),
                 (source.REGIMES[1],),[c0,c1,15],3)
            if changed!=value:
                raise AssertionError("F124CZ_THIRD_DERIVATIVE_CONSTANT_SAFETY")
            tested+=1
    return tested

def quadratic_witness():
    import random
    verified=[]
    for seed in source.SEEDS:
        rng=random.Random(17102201+seed*997)
        hidden=source.quadratic_parameters(rng)
        found=False
        for output in hidden:
            for i,j in output[1]:
                result=derivative((i,j),(source.REGIMES[0],),hidden,2)
                if result:
                    found=True;break
            if found:break
        if not found:
            raise AssertionError("F124CZ_QUADRATIC_NOT_PROVEN_NONAFFINE")
        verified.append(seed)
    return verified

def main():
    assert derivative.__code__.co_argcount==4
    pairs=carry_witness()
    quadratics=quadratic_witness()
    print("F124CZ_SOURCEONLY_CARRY_THIRD_DERIVATIVE_ALL_CONSTANTS=PASS")
    print("F124CZ_CARRY_NONDEGREE2_CONSTANT_PAIRS="+str(pairs))
    print("F124CZ_QUADRATIC_NONAFFINE_SEEDS="+json.dumps(quadratics))
    print("F124CZ_SCIENTIFIC_FIRSTUSE=FALSE")

if __name__=="__main__":main()
