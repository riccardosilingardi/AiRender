<?xml version='1.0' encoding='UTF-8'?>
<!-- Sonda usa e getta del prompt 15: scritta a mano, non generata. -->
<Element xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="https://pythonparts.allplan.com/2026/schemas/PythonPart.xsd">
<Script>
<Name>riccardo_silingardi\airender\AirenderSondaMateriali.py</Name>
<Title>AIRENDER sonda materiali</Title>
<Version>0.1</Version>
</Script>
<Page>
<Name>Pagina</Name>
<Text>AIRENDER sonda materiali</Text>
<Parameters>
<Parameter>
<Name>Spiegazione</Name>
<Text>Premi i pulsanti dall'alto in basso. Non cambia il modello e non manda niente a nessun servizio. Tutto finisce in Usr\...\AIRENDER\sonda-materiali</Text>
<ValueType>Text</ValueType>
</Parameter>
<Parameter>
<Name>RigaApi</Name>
<Text>1 · Cosa sa l'API</Text>
<ValueType>Row</ValueType>
<Parameters>
<Parameter>
<Name>Api</Name>
<Text>Elenca l'API</Text>
<EventId>3001</EventId>
<ValueType>Button</ValueType>
</Parameter>
</Parameters>
</Parameter>
<Parameter>
<Name>RigaElementi</Name>
<Text>2 · Materiali del modello</Text>
<ValueType>Row</ValueType>
<Parameters>
<Parameter>
<Name>Elementi</Name>
<Text>Leggi gli elementi</Text>
<EventId>3002</EventId>
<ValueType>Button</ValueType>
</Parameter>
</Parameters>
</Parameter>
<Parameter>
<Name>RigaNormale</Name>
<Text>3 · Vista com'e' di solito</Text>
<ValueType>Row</ValueType>
<Parameters>
<Parameter>
<Name>Normale</Name>
<Text>Salva vista normale</Text>
<EventId>3003</EventId>
<ValueType>Button</ValueType>
</Parameter>
</Parameters>
</Parameter>
<Parameter>
<Name>RigaColormap</Name>
<Text>4 · Stessa camera, in color map</Text>
<ValueType>Row</ValueType>
<Parameters>
<Parameter>
<Name>Colormap</Name>
<Text>Salva color map</Text>
<EventId>3004</EventId>
<ValueType>Button</ValueType>
</Parameter>
</Parameters>
</Parameter>
<Parameter>
<Name>RigaCartella</Name>
<Text>5 · Da rimandare</Text>
<ValueType>Row</ValueType>
<Parameters>
<Parameter>
<Name>Cartella</Name>
<Text>Apri la cartella</Text>
<EventId>3005</EventId>
<ValueType>Button</ValueType>
</Parameter>
</Parameters>
</Parameter>
</Parameters>
</Page>
</Element>
