<?xml version='1.0' encoding='UTF-8'?>
<!-- Sonda usa e getta della color map da Allplan (2026-11-01): scritta a mano, non generata. -->
<Element xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="https://pythonparts.allplan.com/2026/schemas/PythonPart.xsd">
<Script>
<Name>riccardo_silingardi\airender\AirenderSondaColormap.py</Name>
<Title>AIRENDER sonda color map</Title>
<Version>0.1</Version>
</Script>
<Page>
<Name>Pagina</Name>
<Text>AIRENDER sonda color map</Text>
<Parameters>
<Parameter>
<Name>Spiegazione</Name>
<Text>CAMBIA LE SUPERFICI degli elementi: usala solo su una COPIA del progetto. Non manda niente a nessun servizio. Tutto finisce in Usr\...\AIRENDER\sonda-colormap</Text>
<ValueType>Text</ValueType>
</Parameter>
<Parameter>
<Name>Copia</Name>
<Text>Ho aperto una COPIA del progetto</Text>
<Value>False</Value>
<ValueType>CheckBox</ValueType>
</Parameter>
<Parameter>
<Name>RigaNormale</Name>
<Text>1 · Vista com'e' di solito</Text>
<ValueType>Row</ValueType>
<Parameters>
<Parameter>
<Name>Normale</Name>
<Text>Salva vista normale</Text>
<EventId>3101</EventId>
<ValueType>Button</ValueType>
</Parameter>
</Parameters>
</Parameter>
<Parameter>
<Name>RigaLeggi</Name>
<Text>2 · Materiali degli elementi selezionati</Text>
<ValueType>Row</ValueType>
<Parameters>
<Parameter>
<Name>Leggi</Name>
<Text>Leggi i materiali</Text>
<EventId>3102</EventId>
<ValueType>Button</ValueType>
</Parameter>
</Parameters>
</Parameter>
<Parameter>
<Name>RigaColora</Name>
<Text>3 · Solo sulla COPIA</Text>
<ValueType>Row</ValueType>
<Parameters>
<Parameter>
<Name>Colora</Name>
<Text>Colora per materiale</Text>
<EventId>3103</EventId>
<ValueType>Button</ValueType>
</Parameter>
</Parameters>
</Parameter>
<Parameter>
<Name>RigaColormap</Name>
<Text>4 · Stessa camera</Text>
<ValueType>Row</ValueType>
<Parameters>
<Parameter>
<Name>Colormap</Name>
<Text>Salva color map</Text>
<EventId>3104</EventId>
<ValueType>Button</ValueType>
</Parameter>
</Parameters>
</Parameter>
<Parameter>
<Name>RigaRimetti</Name>
<Text>5 · Torna com'era</Text>
<ValueType>Row</ValueType>
<Parameters>
<Parameter>
<Name>Rimetti</Name>
<Text>Rimetti le superfici</Text>
<EventId>3105</EventId>
<ValueType>Button</ValueType>
</Parameter>
</Parameters>
</Parameter>
<Parameter>
<Name>RigaCartella</Name>
<Text>6 · Da rimandare</Text>
<ValueType>Row</ValueType>
<Parameters>
<Parameter>
<Name>Cartella</Name>
<Text>Apri la cartella</Text>
<EventId>3106</EventId>
<ValueType>Button</ValueType>
</Parameter>
</Parameters>
</Parameter>
</Parameters>
</Page>
</Element>
