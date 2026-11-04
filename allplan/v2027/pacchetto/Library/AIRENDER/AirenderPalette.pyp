<?xml version='1.0' encoding='UTF-8'?>
<!-- Generato da allplan/v2027/scrivi_palette_pyp.py: non modificare a mano. -->
<Element xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="https://pythonparts.allplan.com/2026/schemas/PythonPart.xsd">
<Script>
<Name>riccardo_silingardi\airender\AirenderPalette.py</Name>
<Title>AIRENDER</Title>
<Version>1.0</Version>
</Script>
<Page>
<Name>Pagina</Name>
<Text>AIRENDER</Text>
<Parameters>
<Parameter>
<Name>ImmaginiDaScript</Name>
<Value>0</Value>
<ValueType>Integer</ValueType>
<Visible>False</Visible>
</Parameter>
<Parameter>
<Name>UltimaVista</Name>
<Value></Value>
<ValueType>String</ValueType>
<Visible>False</Visible>
</Parameter>
<Parameter>
<Name>Chiudi</Name>
<Text>Per tornare alla Library premi Esc. I render in corso continuano.</Text>
<ValueType>Text</ValueType>
</Parameter>
<Parameter>
<Name>Sezione1</Name>
<Text>Vista</Text>
<ValueType>Expander</ValueType>
<Parameters>
<Parameter>
<Name>VistaNome</Name>
<Text>Vista</Text>
<Value></Value>
<ValueType>String</ValueType>
<Enable>False</Enable>
</Parameter>
<Parameter>
<Name>VistaImmagine</Name>
<Value>palette_nessuna.png</Value>
<Orientation>Middle</Orientation>
<ValueType>Picture</ValueType>
<Visible>ImmaginiDaScript == 1</Visible>
</Parameter>
<Parameter>
<Name>VistaEsito</Name>
<Text>Esito</Text>
<Value></Value>
<ValueType>String</ValueType>
<Enable>False</Enable>
</Parameter>
<Parameter>
<Name>RigaCattura</Name>
<Text>Finestra attiva</Text>
<ValueType>Row</ValueType>
<Parameters>
<Parameter>
<Name>Cattura</Name>
<Text>Cattura vista</Text>
<EventId>1001</EventId>
<ValueType>Button</ValueType>
</Parameter>
</Parameters>
</Parameter>
<Parameter>
<Name>Dimensione</Name>
<Text>Dimensione</Text>
<Value>0</Value>
<ValueType>RadioButtonGroup</ValueType>
<Parameters>
<Parameter>
<Name>Dimensione0</Name>
<Text>Come la finestra</Text>
<Value>0</Value>
<ValueType>RadioButton</ValueType>
</Parameter>
<Parameter>
<Name>Dimensione1</Name>
<Text>1920 × 1080</Text>
<Value>1</Value>
<ValueType>RadioButton</ValueType>
</Parameter>
<Parameter>
<Name>Dimensione2</Name>
<Text>3840 × 2160</Text>
<Value>2</Value>
<ValueType>RadioButton</ValueType>
</Parameter>
</Parameters>
</Parameter>
<Parameter>
<Name>Formato</Name>
<Text>Formato</Text>
<Value>Come la finestra</Value>
<ValueList>Come la finestra|21:9 panoramico|16:9|3:2|4:3|1:1 quadrato|3:4 verticale|2:3 verticale|9:16 verticale</ValueList>
<ValueType>StringComboBox</ValueType>
</Parameter>
<Parameter>
<Name>RigaTaglio</Name>
<Text>Taglio</Text>
<ValueType>Row</ValueType>
<Parameters>
<Parameter>
<Name>VediTaglio</Name>
<Text>Vedi cosa ha tagliato</Text>
<EventId>1008</EventId>
<ValueType>Button</ValueType>
</Parameter>
</Parameters>
</Parameter>
</Parameters>
</Parameter>
<Parameter>
<Name>Sezione2</Name>
<Text>Studio</Text>
<ValueType>Expander</ValueType>
<Parameters>
<Parameter>
<Name>NelloStudio</Name>
<Text>Stile, render, ritocchi e video si fanno nello Studio.</Text>
<ValueType>Text</ValueType>
</Parameter>
<Parameter>
<Name>RigaStudio</Name>
<Text>Studio</Text>
<ValueType>Row</ValueType>
<Parameters>
<Parameter>
<Name>ApriStudio</Name>
<Text>Apri nello Studio</Text>
<EventId>1006</EventId>
<ValueType>Button</ValueType>
</Parameter>
<Parameter>
<Name>ApriCartella</Name>
<Text>Apri cartella</Text>
<EventId>1007</EventId>
<ValueType>Button</ValueType>
</Parameter>
</Parameters>
</Parameter>
</Parameters>
</Parameter>
<Parameter>
<Name>Cartella</Name>
<Text>Cartella delle viste (vuota = Usr\AIRENDER\viste)</Text>
<Value></Value>
<ValueType>String</ValueType>
</Parameter>
</Parameters>
</Page>
</Element>
