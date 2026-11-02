<?xml version='1.0' encoding='UTF-8'?>
<!-- Sonda usa e getta della color map da Allplan (2026-11-02): scritta a mano, non generata. -->
<Element xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="https://pythonparts.allplan.com/2026/schemas/PythonPart.xsd">
<Script>
<Name>riccardo_silingardi\airender\AirenderSondaColormap.py</Name>
<Title>AIRENDER sonda color map</Title>
<Version>0.2</Version>
</Script>
<Page>
<Name>Pagina</Name>
<Text>AIRENDER sonda color map</Text>
<Parameters>
<Parameter>
<Name>Spiegazione1</Name>
<Text>Prova la color map dai materiali di Allplan.</Text>
<ValueType>Text</ValueType>
</Parameter>
<Parameter>
<Name>Spiegazione2</Name>
<Text>CAMBIA LE SUPERFICI: usala solo su una COPIA.</Text>
<ValueType>Text</ValueType>
</Parameter>
<Parameter>
<Name>Spiegazione3</Name>
<Text>Prima: finestra 3D come di solito.</Text>
<ValueType>Text</ValueType>
</Parameter>
<Parameter>
<Name>Copia</Name>
<Text>Ho aperto una COPIA</Text>
<Value>False</Value>
<ValueType>CheckBox</ValueType>
</Parameter>
<Parameter>
<Name>RigaColora</Name>
<Text>1</Text>
<ValueType>Row</ValueType>
<Parameters>
<Parameter>
<Name>Colora</Name>
<Text>Colora</Text>
<EventId>3101</EventId>
<ValueType>Button</ValueType>
</Parameter>
</Parameters>
</Parameter>
<Parameter>
<Name>RigaSalva</Name>
<Text>2 · camera ferma</Text>
<ValueType>Row</ValueType>
<Parameters>
<Parameter>
<Name>Salva</Name>
<Text>Salva e rimetti</Text>
<EventId>3102</EventId>
<ValueType>Button</ValueType>
</Parameter>
</Parameters>
</Parameter>
<Parameter>
<Name>RigaCartella</Name>
<Text>3</Text>
<ValueType>Row</ValueType>
<Parameters>
<Parameter>
<Name>Cartella</Name>
<Text>Apri la cartella</Text>
<EventId>3103</EventId>
<ValueType>Button</ValueType>
</Parameter>
</Parameters>
</Parameter>
</Parameters>
</Page>
</Element>
